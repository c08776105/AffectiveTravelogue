import requests
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

from services.neo4j_service import neo4j_service
from utils.config import settings
from utils.logger import logger
from utils.osm_client import osm_client


class RAGService:
    def __init__(self):
        self.llm = OllamaLLM(
            base_url=settings.OLLAMA_HOST, model=settings.LLM_MODEL, temperature=0.7
        )

    def build_context(self, route_id: str):
        """
        Fetch waypoints, query POIs, and construct context string.
        """
        route = neo4j_service.get_route(route_id)
        if not route:
            return None, None

        waypoints = neo4j_service.get_waypoints(route_id)

        context_parts = []
        for wp in waypoints:
            pois = osm_client.query_pois(wp["latitude"], wp["longitude"])
            wp_context = f"Waypoint at ({wp['latitude']}, {wp['longitude']}):\n"
            if wp["text_note"]:
                wp_context += f"- User Note: {wp['text_note']}\n"
            if pois:
                wp_context += f"- Nearby Features: {', '.join([p['name'] + ' (' + str(p['type']) + ')' for p in pois[:5]])}\n"
            context_parts.append(wp_context)

        return route, chr(10).join(context_parts)

    def generate_travelogue(self, route_id: str) -> str:
        route, context_data = self.build_context(route_id)
        if not route:
            return "Route not found."

        # Define the LangChain Prompt Template
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a psychogeographic storyteller. Your goal is to synthesise a cohesive, "
                    "evocative travelogue based on a series of waypoints collected during a walk. "
                    "Use the provided user observations and environmental context (points of interest) to create "
                    "a narrative that feels authentic and reflects the emotional and spatial journey.",
                ),
                (
                    "user",
                    "Route Name: {route_name}\n\nJourney Data:\n{context}\n\n"
                    "Please generate a detailed travelogue that weaves these observations and features into a continuous story of the walk.",
                ),
            ]
        )

        # Create the LangChain processing pipeline
        chain = prompt | self.llm | StrOutputParser()

        try:
            logger.info(f"Generating travelogue via LangChain for route: {route_id}")
            response = chain.invoke(
                {"route_name": route["name"], "context": context_data}
            )
            return response
        except Exception as e:
            logger.error(f"LangChain generation failed: {e}")
            return f"Generation failed: {str(e)}"


rag_service = RAGService()
