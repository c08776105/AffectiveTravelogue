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

        with open("system_prompt.txt", "r") as sys_prompt_file:
            system_prompt_text = sys_prompt_file.read();

        self.system_prompt = system_prompt_text

    def build_context(self, route_id: str):
        """
        Fetch waypoints, query POIs, and construct context string.
        All waypoints are sent to Overpass in a single batched API call.
        """
        route = neo4j_service.get_route(route_id)
        if not route:
            return None, None

        waypoints = neo4j_service.get_waypoints(route_id)
        if not waypoints:
            return route, ""

        # One API call for all waypoints instead of one per waypoint
        poi_map = osm_client.query_pois_for_waypoints(waypoints, radius=settings.OSM_POI_RADIUS_METERS)

        context_parts = []
        for i, wp in enumerate(waypoints):
            pois = poi_map.get(i, [])
            # NOTE: text_note is deliberately excluded here. The AI travelogue
            # must be generated from objective spatial data only (coordinates +
            # OSM POIs). Human notes are withheld until the evaluation step so
            # the BERTScore comparison is a genuine independent measure.
            wp_context = f"Waypoint at ({wp['latitude']}, {wp['longitude']}):\n"
            if pois:
                wp_context += f"- Nearby Features: {', '.join([p['name'] + ' (' + str(p['type']) + ')' for p in pois[:5]])}\n"
            else:
                wp_context += "- Nearby Features: none recorded\n"
            context_parts.append(wp_context)

        return route, chr(10).join(context_parts)

    def _first_note(self, waypoint: dict) -> str:
        """Extract the human text note from a single waypoint dict."""
        import json
        raw = waypoint.get("text_note")
        if not raw:
            return ""
        try:
            parsed = json.loads(raw)
            text = parsed.get("text") or parsed.get("content") or raw
        except (json.JSONDecodeError, AttributeError, TypeError):
            text = raw
        return text.strip() if text else ""

    def generate_travelogue(self, route_id: str, llm_model: str | None = None, prompt_type: str = "zero_shot") -> dict:
        route, context_data = self.build_context(route_id)
        effective_model = llm_model or settings.LLM_MODEL
        if not route:
            return {"text": "Route not found.", "llm_model": effective_model, "prompt_type": prompt_type}

        llm = (
            OllamaLLM(base_url=settings.OLLAMA_HOST, model=effective_model, temperature=0.7)
            if effective_model != settings.LLM_MODEL
            else self.llm
        )

        user_instruction = (
            "Route Name: {route_name}\n\nSpatial Data:\n{context}\n\n"
            "Write a detailed psychogeographic travelogue of this walk based only on the locations and nearby features listed above."
        )

        messages = [("system", self.system_prompt)]

        if prompt_type == "few_shot":
            example = neo4j_service.get_example_for_few_shot(route_id)
            if example:
                wp = example["waypoint"]
                note = self._first_note(wp)
                if note:
                    poi_map = osm_client.query_pois_for_waypoints([wp], radius=settings.OSM_POI_RADIUS_METERS)
                    pois = poi_map.get(0, [])
                    wp_context = f"Waypoint at ({wp['latitude']}, {wp['longitude']}):\n"
                    if pois:
                        wp_context += f"- Nearby Features: {', '.join([p['name'] + ' (' + str(p['type']) + ')' for p in pois[:5]])}\n"
                    else:
                        wp_context += "- Nearby Features: none recorded\n"
                    example_input = (
                        f"Route Name: {example['route_name']}\n\nSpatial Data:\n{wp_context}\n"
                        "Write a detailed psychogeographic travelogue of this walk based only on the locations and nearby features listed above."
                    )
                    messages.append(("user", example_input))
                    messages.append(("ai", note))
                    logger.info(f"Few-shot: injected example from route '{example['route_name']}'")
                else:
                    logger.info("Few-shot: example waypoint had no note, falling back to zero-shot")
            else:
                logger.info("Few-shot: no suitable example route found, falling back to zero-shot")

        messages.append(("user", user_instruction))
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | llm | StrOutputParser()

        try:
            logger.info(f"Generating travelogue [{prompt_type}, model={effective_model}] for route: {route_id}")
            response = chain.invoke({"route_name": route["name"], "context": context_data})
            return {"text": response, "llm_model": effective_model, "prompt_type": prompt_type}
        except Exception as e:
            logger.error(f"LangChain generation failed: {e}")
            return {"text": f"Generation failed: {str(e)}", "llm_model": effective_model, "prompt_type": prompt_type}

    def llm_accessible(self) -> str:
        try:
            response = requests.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                print(response.json())
                model_found = any(settings.LLM_MODEL in m for m in models)
                if model_found:
                    return "up"
                else:
                    return "model not found"
            return "down"
        except Exception as e:
            logger.error(f"LLM service connectivity failed: {e}")
            return "down"


rag_service = RAGService()
