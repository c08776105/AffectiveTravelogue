import re

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
            system_prompt_text = sys_prompt_file.read()

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

        poi_map = neo4j_service.get_cached_pois_for_waypoints(waypoints)
        if poi_map is None:
            logger.info(f"OSM cache miss for route {route_id}, fetching from API")
            poi_map = osm_client.query_pois_for_waypoints(
                waypoints, radius=settings.OSM_POI_RADIUS_METERS
            )
            neo4j_service.store_pois_for_waypoints(waypoints, poi_map)
        else:
            logger.info(f"OSM cache hit for route {route_id}")

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

    def _generate_meta_prompt(self, route_id: str, llm) -> str:
        """
        Pass 1 of meta-prompting: analyse the user's own waypoint notes to derive
        their writing style, then ask the LLM to produce a custom system prompt
        that will guide Pass 2 to match that style.
        Returns the dynamic system prompt string, or falls back to the default.
        """
        waypoints = neo4j_service.get_waypoints(route_id)
        notes = [self._first_note(wp) for wp in waypoints]
        notes = [n for n in notes if n][:3]

        if not notes:
            logger.info("Meta-prompt: no notes found, using default system prompt")
            return self.system_prompt

        numbered = "\n".join(f"{i + 1}. {note}" for i, note in enumerate(notes))
        meta_instruction = (
            "You are an expert prompt engineer and computational linguist. Read the walker's observations below:\n\n"
            f"{numbered}\n\n"
            "PHASE 1: LINGUISTIC ANALYSIS\n"
            "Before writing the prompt, you must explicitly analyze the text across these vectors. Output your findings:\n"
            "1. Average Sentence Length: (Short/Medium/Long?)\n"
            "2. Clause Structure: (How does the author combine sentences?)\n"
            "3. Paragraph Openers: (Give examples of how the author starts paragraphs. e.g., 'As we...', 'After...').\n"
            "4. Register: (Is it academic, conversational, embodied, analytical?)\n"
            "5. Verbs and Action: (Does the author use passive observation or active physical movement?)\n\n"
            "PHASE 2: PROMPT GENERATION\n"
            "Using your analysis, write the final system prompt for an AI language model. "
            "The system prompt MUST include the following:\n"
            "- A strict instruction to write one paragraph per waypoint.\n"
            "- A strict instruction to preserve grounding rules (no invented entities or places).\n"
            "- 'SYNTACTIC RULES': A list of 3 to 4 hard grammatical constraints the AI must follow to match the human's style (e.g., 'Use active verbs for movement', 'Begin paragraphs with a time or action transition').\n"
            "- A strict instruction to avoid clinical, academic, or analytical phrasing. Do not summarize or theorize about the landscape.\n\n"
            "Format your output exactly like this:\n"
            "[ANALYSIS]\n"
            "(Your Phase 1 work here)\n\n"
            "[SYSTEM_PROMPT]\n"
            "(Your Phase 2 prompt here)"
        )

        try:
            meta_response = llm.invoke(meta_instruction)
            match = re.search(
                r"\[SYSTEM_PROMPT\]\s*(.*)", meta_response, re.IGNORECASE | re.DOTALL
            )
            dynamic_prompt = match.group(1).strip()
            if isinstance(dynamic_prompt, str) and len(dynamic_prompt.strip()) > 50:
                logger.info(
                    f"Meta-prompt: generated dynamic system prompt ({len(dynamic_prompt)} chars)"
                )
                return dynamic_prompt.strip()
        except Exception as e:
            logger.error(f"Meta-prompt generation failed: {e}")

        logger.warning(
            "Meta-prompt: LLM returned unusable output, falling back to default"
        )
        return self.system_prompt

    def generate_travelogue(
        self,
        route_id: str,
        llm_model: str | None = None,
        prompt_type: str = "zero_shot",
        use_meta_prompt: bool = False,
    ) -> dict:
        route, context_data = self.build_context(route_id)
        effective_model = llm_model or settings.LLM_MODEL
        if not route:
            return {
                "text": "Route not found.",
                "llm_model": effective_model,
                "prompt_type": prompt_type,
                "meta_prompted": False,
            }

        llm = (
            OllamaLLM(
                base_url=settings.OLLAMA_HOST, model=effective_model, temperature=0.7
            )
            if effective_model != settings.LLM_MODEL
            else self.llm
        )

        user_instruction = (
            "Route Name: {route_name}\n\nSpatial Data:\n{context}\n\n"
            "Write a psychogeographic travelogue of this walk. "
            "Write exactly one paragraph per waypoint listed above, in the same order. "
            "Separate each paragraph with a blank line. "
            "Each paragraph should be 2–5 sentences, grounded in what the spatial data tells you about that specific location. "
            "Use only the locations and nearby features listed above — do not invent."
        )

        if use_meta_prompt:
            system_prompt = self._generate_meta_prompt(route_id, llm)
        else:
            system_prompt = self.system_prompt

        messages = [("system", system_prompt)]

        if prompt_type == "few_shot":
            example = neo4j_service.get_example_for_few_shot(route_id)
            if example:
                example_wps = example["waypoints"]
                notes = [self._first_note(wp) for wp in example_wps]
                notes = [n for n in notes if n]
                if notes:
                    poi_map = neo4j_service.get_cached_pois_for_waypoints(example_wps)
                    if poi_map is None:
                        poi_map = osm_client.query_pois_for_waypoints(
                            example_wps, radius=settings.OSM_POI_RADIUS_METERS
                        )
                        neo4j_service.store_pois_for_waypoints(example_wps, poi_map)
                    context_parts = []
                    for i, wp in enumerate(example_wps):
                        pois = poi_map.get(i, [])
                        wp_context = (
                            f"Waypoint at ({wp['latitude']}, {wp['longitude']}):\n"
                        )
                        if pois:
                            wp_context += f"- Nearby Features: {', '.join([p['name'] + ' (' + str(p['type']) + ')' for p in pois[:5]])}\n"
                        else:
                            wp_context += "- Nearby Features: none recorded\n"
                        context_parts.append(wp_context)
                    example_input = (
                        f"Route Name: {example['route_name']}\n\nSpatial Data:\n{chr(10).join(context_parts)}\n"
                        "Write a travelogue of this walk. "
                        "Write exactly one paragraph per waypoint, separated by blank lines. "
                        "Use only the locations and nearby features listed above."
                    )
                    messages.append(("user", example_input))
                    messages.append(("ai", "\n\n".join(notes)))
                    logger.info(
                        f"Few-shot: injected {len(notes)} waypoint(s) from route '{example['route_name']}'"
                    )
                else:
                    logger.info(
                        "Few-shot: example waypoints had no notes, falling back to zero-shot"
                    )
            else:
                logger.info(
                    "Few-shot: no suitable example route found, falling back to zero-shot"
                )

        messages.append(("user", user_instruction))
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | llm | StrOutputParser()

        try:
            logger.info(
                f"Generating travelogue [{prompt_type}, meta={use_meta_prompt}, model={effective_model}] for route: {route_id}"
            )
            response = chain.invoke(
                {"route_name": route["name"], "context": context_data}
            )
            return {
                "text": response,
                "llm_model": effective_model,
                "prompt_type": prompt_type,
                "meta_prompted": use_meta_prompt,
            }
        except Exception as e:
            logger.error(f"LangChain generation failed: {e}")
            return {
                "text": f"Generation failed: {str(e)}",
                "llm_model": effective_model,
                "prompt_type": prompt_type,
                "meta_prompted": False,
            }

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
