import json as _json
import re

import requests
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

from services.neo4j_service import neo4j_service
from utils.config import settings
from utils.elevation_client import elevation_client
from utils.logger import logger
from utils.osm_client import osm_client

_SALIENCE_SYSTEM_PROMPT = """\
You are a spatial data ranker operating on the principles of cognitive geography. \
Your task is to rank raw OpenStreetMap Points of Interest (POIs) by their human \
salience for a person on foot.

---
RANKING TIERS:

HIGH — Immediately noticeable, physically prominent, or culturally significant. \
A walker would almost certainly register it. \
Examples: rivers, lakes, named bridges, church spires, ruins, named pubs/bars, \
prominent monuments, summits, waterfalls, named parks, notable viewpoints.

MEDIUM — Present and may be noticed, but not dominant. A walker might mention it in passing. \
Examples: car parks, sports facilities, schools, named roads or junctions, \
small shops, post offices, minor memorials, named residential streets.

LOW — Unlikely to register consciously. Infrastructure, administrative, or generic. \
Examples: waste baskets, bicycle parking, post boxes, street lamps, fences, \
power lines, unnamed landuse boundaries, underground infrastructure, \
parish boundaries, generic unnamed buildings.

---
OUTPUT RULES:
- Respond with valid JSON only. No explanation, no markdown, no code fences.
- Every POI must appear in exactly one tier.
- Use this exact structure:

{{"waypoints":[{{"index":0,"high":["Name1","Name2"],"medium":["Name3"],"low":["Name4"]}},{{"index":1,"high":[],"medium":["Name5"],"low":[]}}]}}
"""


class OllamaTokenCallback(BaseCallbackHandler):
    def __init__(self):
        self.prompt_tokens = None
        self.completion_tokens = None

    def on_llm_end(self, response, **kwargs):
        # Token counts live in generation_info for OllamaLLM
        for gen_list in response.generations:
            for gen in gen_list:
                info = getattr(gen, "generation_info", None) or {}
                self.prompt_tokens = info.get("prompt_eval_count")
                self.completion_tokens = info.get("eval_count")


class RAGService:
    def __init__(self):
        self.llm = OllamaLLM(
            base_url=settings.OLLAMA_HOST,
            model=settings.LLM_MODEL,
            reasoning=True,
            temperature=0.7,
            num_ctx=8192,
            num_predict=2048,  # Change to allow for large numbers of POIs to process during salience ranking
        )

        self.salience_llm = OllamaLLM(
            base_url=settings.OLLAMA_HOST,
            model=settings.LLM_MODEL,
            temperature=0.1,
            num_predict=2024,  # should handle salience ranking errors with truncated json
        )

        with open("system_prompt.txt", "r") as sys_prompt_file:
            system_prompt_text = sys_prompt_file.read()

        self.system_prompt = system_prompt_text

    # ------------------------------------------------------------------
    # Data layer: waypoints, POIs, elevation (all with Neo4j caching)
    # ------------------------------------------------------------------

    def _fetch_poi_map(self, waypoints: list[dict]) -> dict[int, list[dict]]:
        """Return poi_map from Neo4j cache, falling back to OSM on a miss."""
        poi_map = neo4j_service.get_cached_pois_for_waypoints(waypoints)
        if poi_map is None:
            poi_map = osm_client.query_pois_for_waypoints(
                waypoints, radius=settings.OSM_POI_RADIUS_METERS
            )
            neo4j_service.store_pois_for_waypoints(waypoints, poi_map)
        return poi_map

    def _fetch_elevations(self, waypoints: list[dict]) -> list[float | None]:
        """Return per-waypoint elevations from Neo4j cache, falling back to API on a miss."""
        elevations = neo4j_service.get_cached_elevations_for_waypoints(waypoints)
        if elevations is None:
            logger.info("Elevation cache miss, fetching from API")
            elevations = elevation_client.get_elevations(waypoints)
            neo4j_service.store_elevations_for_waypoints(waypoints, elevations)
        else:
            logger.info("Elevation cache hit")
        return elevations

    def build_context(self, route_id: str) -> tuple:
        """
        Fetch route, waypoints, raw POI map, and elevations.
        Returns (route, waypoints, poi_map, elevations).
        Context string is built separately so the salience ranker can run first.
        """
        route = neo4j_service.get_route(route_id)
        if not route:
            return None, [], {}, []

        waypoints = neo4j_service.get_waypoints(route_id)
        if not waypoints:
            return route, [], {}, []

        poi_map = self._fetch_poi_map(waypoints)
        elevations = self._fetch_elevations(waypoints)

        logger.info(
            f"Context loaded for route {route_id}: "
            f"{len(waypoints)} waypoints, "
            f"{sum(len(v) for v in poi_map.values())} POIs"
        )
        return route, waypoints, poi_map, elevations

    def _rank_pois_salience(
        self, poi_map: dict[int, list[dict]], llm
    ) -> dict[int, list[dict]]:

        if not any(pois for pois in poi_map.values()):
            return poi_map

        lines = []
        for i, pois in sorted(poi_map.items()):
            formatted = (
                ", ".join(f"{p['name']} ({p['type']})" for p in pois)
                if pois
                else "none"
            )
            lines.append(f"Waypoint {i}:\n{formatted}")

        try:
            rank_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", _SALIENCE_SYSTEM_PROMPT),
                    ("user", "{pois}"),
                ]
            )
            response: str = (rank_prompt | llm | StrOutputParser()).invoke(
                {"pois": "\n\n".join(lines)}
            )

            # Strip markdown code fences if model wraps output anyway
            cleaned = re.sub(r"```(?:json)?|```", "", response).strip()

            # Extract the first JSON object found — handles preamble text
            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not json_match:
                raise ValueError(f"No JSON object found in response: {cleaned[:200]}")

            data = _json.loads(json_match.group())

            # Build name → tier lookup
            name_to_tier: dict[str, str] = {}
            for wp in data.get("waypoints", []):
                for name in wp.get("high", []):
                    name_to_tier[name] = "HIGH"
                for name in wp.get("medium", []):
                    name_to_tier[name] = "MEDIUM"
                for name in wp.get("low", []):
                    name_to_tier[name] = "LOW"

            # Annotate original POI dicts
            ranked_map: dict[int, list[dict]] = {}
            for i, pois in poi_map.items():
                ranked_map[i] = [
                    {**p, "salience": name_to_tier.get(p["name"], "MEDIUM")}
                    for p in pois
                ]

            total = sum(len(v) for v in ranked_map.values())
            high = sum(
                1 for v in ranked_map.values() for p in v if p.get("salience") == "HIGH"
            )
            low = sum(
                1 for v in ranked_map.values() for p in v if p.get("salience") == "LOW"
            )
            logger.info(
                f"Salience ranking: {total} POIs total — {high} HIGH, {total - high - low} MEDIUM, {low} LOW"
            )
            return ranked_map

        except Exception as e:
            logger.error(
                f"Salience ranking failed: {e}, defaulting all POIs to MEDIUM.\nGenerated result: {response}"
            )

            # Fall back and return medium salience for every point of interest
            return {
                i: [{**p, "salience": "MEDIUM"} for p in pois]
                for i, pois in poi_map.items()
            }

    # ------------------------------------------------------------------
    # Context string formatter
    # ------------------------------------------------------------------

    @staticmethod
    def _format_context_string(
        waypoints: list[dict],
        poi_map: dict[int, list[dict]],
        elevations: list[float | None],
    ) -> str:
        parts = []
        for i, wp in enumerate(waypoints):
            pois = poi_map.get(i, [])

            # Elevation line
            elev = elevations[i] if i < len(elevations) else None
            if elev is not None:
                elev_str = f"{int(round(elev))}m"
                if i > 0:
                    prev_elev = elevations[i - 1] if i - 1 < len(elevations) else None
                    if prev_elev is not None:
                        delta = int(round(elev - prev_elev))
                        arrow = "↑" if delta >= 0 else "↓"
                        elev_str += f" ({arrow}{abs(delta):+d}m)"
                elev_line = f" | Elevation: {elev_str}"
            else:
                elev_line = ""

            # NOTE: text_note is deliberately excluded here. The AI travelogue
            # must be generated from objective spatial data only (coordinates +
            # OSM POIs). Human notes are withheld until the evaluation step so
            # the BERTScore comparison is a genuine independent measure.
            header = f"Waypoint at ({wp['latitude']:.5f}, {wp['longitude']:.5f}){elev_line}:\n"

            if not pois:
                parts.append(header + "- Nearby Features: none recorded\n")
                continue

            # Split into tiers
            high = [p for p in pois if p.get("salience") == "HIGH"]
            medium = [p for p in pois if p.get("salience") == "MEDIUM"]
            low = [p for p in pois if p.get("salience") == "LOW"]

            def _fmt(lst: list[dict]) -> str:
                return ", ".join(f"{p['name']} ({p['type']})" for p in lst[:5])

            lines = header
            if high:
                lines += f"- Key Features: {_fmt(high)}\n"
            if medium:
                lines += f"- Also Present: {_fmt(medium)}\n"
            if low:
                lines += f"- Background: {_fmt(low)}\n"
            if not high and not medium and not low:
                lines += "- Nearby Features: none recorded\n"

            parts.append(lines)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        meta_response = ""

        try:
            meta_response = llm.invoke(meta_instruction)
            match = re.search(
                r"\[SYSTEM_PROMPT\]\s*(.*)", meta_response, re.IGNORECASE | re.DOTALL
            )

            if match is None:  # ← the missing guard
                logger.warning(
                    "Meta-prompt: [SYSTEM_PROMPT] tag not found in LLM response, "
                    f"falling back to default. Response preview: {meta_response}"
                )
                return self.system_prompt

            dynamic_prompt = match.group(1).strip()
            if isinstance(dynamic_prompt, str) and len(dynamic_prompt.strip()) > 50:
                logger.info(
                    f"Meta-prompt: generated dynamic system prompt ({len(dynamic_prompt)} chars)"
                )
                return dynamic_prompt.strip()
        except Exception as e:
            logger.error(
                f"Meta-prompt generation failed: {e}.\nReturned: {meta_response}"
            )

        logger.warning(
            f"Meta-prompt: LLM returned unusable output, falling back to default. Returned: {meta_response}"
        )
        return self.system_prompt

    # ------------------------------------------------------------------
    # Main generation entry point
    # ------------------------------------------------------------------

    def generate_travelogue(
        self,
        route_id: str,
        llm_model: str | None = None,
        prompt_type: str = "zero_shot",
        use_meta_prompt: bool = False,
    ) -> dict:
        effective_model = llm_model or settings.LLM_MODEL
        llm = (
            OllamaLLM(
                base_url=settings.OLLAMA_HOST,
                model=effective_model,
                temperature=self.llm.temperature,
                num_ctx=self.llm.num_ctx,
                num_predict=self.llm.num_predict,
                top_p=self.llm.top_p,
                top_k=self.llm.top_k,
            )
            if effective_model != settings.LLM_MODEL
            else self.llm
        )

        route, waypoints, poi_map, elevations = self.build_context(route_id)
        if not route:
            return {
                "text": "Route not found.",
                "llm_model": effective_model,
                "prompt_type": prompt_type,
                "meta_prompted": False,
            }

        # Rank POIs by salience, then format context string
        poi_map = self._rank_pois_salience(poi_map, self.salience_llm)
        context_data = self._format_context_string(waypoints, poi_map, elevations)

        user_instruction = (
            "Route Name: {route_name}\n\nSpatial Data:\n{context}\n\n"
            "Write a psychogeographic travelogue of this walk. "
            "Write exactly one paragraph per waypoint listed above, in the same order. "
            "Separate each paragraph with a blank line. "
            "Each paragraph should be 2–5 sentences, grounded in what the spatial data tells you about that specific location. "
            "In the Spatial Data, features are labelled by prominence: "
            "'Key Features' are visually or culturally prominent — centre your descriptions on these. "
            "'Also Present' features may be noted briefly if relevant. "
            "'Background' features should generally be omitted. "
            "Use elevation changes to describe ascent, descent, or the flatness of the terrain where notable. "
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
                    example_poi_map = self._fetch_poi_map(example_wps)
                    example_elevations = self._fetch_elevations(example_wps)
                    example_poi_map = self._rank_pois_salience(example_poi_map, llm)
                    example_context = self._format_context_string(
                        example_wps, example_poi_map, example_elevations
                    )
                    example_input = (
                        f"Route Name: {example['route_name']}\n\nSpatial Data:\n{example_context}\n"
                        "Write a travelogue of this walk. "
                        "Write exactly one paragraph per waypoint, separated by blank lines. "
                        "Focus on Key Features; note Also Present items briefly if relevant; omit Background items. "
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
            token_cb = OllamaTokenCallback()
            response = chain.invoke(
                {"route_name": route["name"], "context": context_data},
                config={"callbacks": [token_cb]},
            )

            logger.info(
                f"Tokens — prompt: {token_cb.prompt_tokens}, "
                f"completion: {token_cb.completion_tokens}, "
                f"total: {(token_cb.prompt_tokens or 0) + (token_cb.completion_tokens or 0)}"
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
