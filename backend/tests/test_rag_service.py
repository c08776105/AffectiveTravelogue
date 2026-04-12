"""
Tests for RAGService.

External dependencies (OllamaLLM, neo4j_service, osm_client,
elevation_client) are replaced by MagicMocks in every test.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import ELEVATIONS, POI_MAP, WAYPOINTS


# ===========================================================================
# _first_note
# ===========================================================================

class TestFirstNote:

    def test_plain_string_returned_as_is(self, rag_svc):
        svc, _ = rag_svc
        assert svc._first_note({"text_note": "Hello world"}) == "Hello world"

    def test_json_with_text_key_extracted(self, rag_svc):
        svc, _ = rag_svc
        raw = json.dumps({"text": "We crossed the bridge."})
        assert svc._first_note({"text_note": raw}) == "We crossed the bridge."

    def test_json_with_content_key_extracted(self, rag_svc):
        svc, _ = rag_svc
        raw = json.dumps({"content": "We reached the summit."})
        assert svc._first_note({"text_note": raw}) == "We reached the summit."

    def test_json_without_text_or_content_returns_raw(self, rag_svc):
        svc, _ = rag_svc
        raw = json.dumps({"other": "value"})
        assert svc._first_note({"text_note": raw}) == raw

    def test_none_text_note_returns_empty(self, rag_svc):
        svc, _ = rag_svc
        assert svc._first_note({"text_note": None}) == ""

    def test_missing_text_note_key_returns_empty(self, rag_svc):
        svc, _ = rag_svc
        assert svc._first_note({}) == ""

    def test_whitespace_stripped(self, rag_svc):
        svc, _ = rag_svc
        assert svc._first_note({"text_note": "  note  "}) == "note"

    def test_invalid_json_treated_as_plain_string(self, rag_svc):
        svc, _ = rag_svc
        assert svc._first_note({"text_note": "{not valid json"}) == "{not valid json"


# ===========================================================================
# _format_context_string
# ===========================================================================

class TestFormatContextString:

    def test_key_features_label_for_high_salience(self, rag_svc):
        svc, _ = rag_svc
        poi_map = {0: [{"name": "Kill River", "type": "waterway:river", "salience": "HIGH"}]}
        result = svc._format_context_string(WAYPOINTS[:1], poi_map, [45.0])
        assert "Key Features:" in result
        assert "Kill River" in result

    def test_also_present_label_for_medium_salience(self, rag_svc):
        svc, _ = rag_svc
        poi_map = {0: [{"name": "Car Park", "type": "amenity:parking", "salience": "MEDIUM"}]}
        result = svc._format_context_string(WAYPOINTS[:1], poi_map, [45.0])
        assert "Also Present:" in result

    def test_background_label_for_low_salience(self, rag_svc):
        svc, _ = rag_svc
        poi_map = {0: [{"name": "unnamed", "type": "amenity:waste_basket", "salience": "LOW"}]}
        result = svc._format_context_string(WAYPOINTS[:1], poi_map, [45.0])
        assert "Background:" in result

    def test_no_pois_produces_none_recorded(self, rag_svc):
        svc, _ = rag_svc
        result = svc._format_context_string(WAYPOINTS[:1], {0: []}, [45.0])
        assert "none recorded" in result

    def test_elevation_shown_on_first_waypoint_without_delta(self, rag_svc):
        svc, _ = rag_svc
        result = svc._format_context_string(WAYPOINTS[:1], {0: []}, [45.0])
        assert "45m" in result
        # First waypoint has no delta arrow
        assert "↑" not in result
        assert "↓" not in result

    def test_elevation_delta_ascent_on_subsequent_waypoint(self, rag_svc):
        svc, _ = rag_svc
        result = svc._format_context_string(
            WAYPOINTS[:2], {0: [], 1: []}, [45.0, 57.0]
        )
        assert "↑" in result
        assert "+12m" in result

    def test_elevation_delta_descent_on_subsequent_waypoint(self, rag_svc):
        svc, _ = rag_svc
        result = svc._format_context_string(
            WAYPOINTS[:2], {0: [], 1: []}, [57.0, 45.0]
        )
        assert "↓" in result

    def test_missing_elevation_omits_elevation_line(self, rag_svc):
        svc, _ = rag_svc
        result = svc._format_context_string(WAYPOINTS[:1], {0: []}, [None])
        assert "Elevation" not in result

    def test_multiple_tiers_all_present(self, rag_svc):
        svc, _ = rag_svc
        poi_map = {
            0: [
                {"name": "River", "type": "waterway:river", "salience": "HIGH"},
                {"name": "Shop", "type": "shop:convenience", "salience": "MEDIUM"},
                {"name": "Bin", "type": "amenity:waste_basket", "salience": "LOW"},
            ]
        }
        result = svc._format_context_string(WAYPOINTS[:1], poi_map, [50.0])
        assert "Key Features:" in result
        assert "Also Present:" in result
        assert "Background:" in result

    def test_waypoint_coordinates_in_output(self, rag_svc):
        svc, _ = rag_svc
        result = svc._format_context_string(WAYPOINTS[:1], {0: []}, [45.0])
        assert "53.24900" in result
        assert "-6.58900" in result


# ===========================================================================
# _rank_pois_salience
# ===========================================================================

class TestRankPoisSalience:

    def _make_llm(self, response_text: str) -> MagicMock:
        llm = MagicMock()
        llm.__or__ = lambda s, other: MagicMock(
            __or__=lambda s2, o2: MagicMock(invoke=MagicMock(return_value=response_text))
        )
        return llm

    def test_empty_poi_map_returned_unchanged(self, rag_svc, mocker):
        svc, _ = rag_svc
        llm = MagicMock()
        empty_map: dict = {0: [], 1: []}
        result = svc._rank_pois_salience(empty_map, llm)
        assert result == empty_map
        llm.assert_not_called()

    def test_salience_field_added_to_each_poi(self, rag_svc, mocker):
        svc, _ = rag_svc
        llm_response = (
            "Waypoint 0 HIGH: Kill River (waterway:river)\n"
            "Waypoint 0 MEDIUM: none\n"
            "Waypoint 0 LOW: unnamed (amenity:waste_basket)\n"
        )
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = llm_response
        mocker.patch("services.rag_service.ChatPromptTemplate.from_messages", return_value=MagicMock(
            __or__=MagicMock(return_value=MagicMock(
                __or__=MagicMock(return_value=mock_chain)
            ))
        ))

        poi_map = {0: [
            {"name": "Kill River", "type": "waterway:river"},
            {"name": "unnamed", "type": "amenity:waste_basket"},
        ]}
        result = svc._rank_pois_salience(poi_map, MagicMock())

        names = {p["name"]: p["salience"] for p in result[0]}
        assert names["Kill River"] == "HIGH"
        assert names["unnamed"] == "LOW"

    def test_llm_exception_defaults_all_to_medium(self, rag_svc, mocker):
        svc, _ = rag_svc
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = RuntimeError("LLM down")
        mocker.patch("services.rag_service.ChatPromptTemplate.from_messages", return_value=MagicMock(
            __or__=MagicMock(return_value=MagicMock(
                __or__=MagicMock(return_value=mock_chain)
            ))
        ))

        poi_map = {0: [{"name": "River", "type": "waterway:river"}]}
        result = svc._rank_pois_salience(poi_map, MagicMock())

        assert result[0][0]["salience"] == "MEDIUM"

    def test_unrecognised_poi_name_defaults_to_medium(self, rag_svc, mocker):
        svc, _ = rag_svc
        # LLM response doesn't mention "Unknown POI"
        llm_response = "Waypoint 0 HIGH: River (waterway:river)\nWaypoint 0 MEDIUM: none\nWaypoint 0 LOW: none\n"
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = llm_response
        mocker.patch("services.rag_service.ChatPromptTemplate.from_messages", return_value=MagicMock(
            __or__=MagicMock(return_value=MagicMock(
                __or__=MagicMock(return_value=mock_chain)
            ))
        ))

        poi_map = {0: [
            {"name": "River", "type": "waterway:river"},
            {"name": "Unknown POI", "type": "amenity:unknown"},
        ]}
        result = svc._rank_pois_salience(poi_map, MagicMock())
        saliences = {p["name"]: p["salience"] for p in result[0]}
        assert saliences.get("Unknown POI") == "MEDIUM"

    def test_all_pois_retained_after_ranking(self, rag_svc, mocker):
        svc, _ = rag_svc
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = RuntimeError("force fallback")
        mocker.patch("services.rag_service.ChatPromptTemplate.from_messages", return_value=MagicMock(
            __or__=MagicMock(return_value=MagicMock(
                __or__=MagicMock(return_value=mock_chain)
            ))
        ))

        poi_map = {0: [
            {"name": "A", "type": "waterway:river"},
            {"name": "B", "type": "amenity:waste_basket"},
            {"name": "C", "type": "amenity:pub"},
        ]}
        result = svc._rank_pois_salience(poi_map, MagicMock())
        assert len(result[0]) == 3  # none removed


# ===========================================================================
# _fetch_poi_map
# ===========================================================================

class TestFetchPoiMap:

    def test_cache_hit_returns_cached_data_without_osm_call(self, rag_svc, mocker):
        svc, _ = rag_svc
        cached = {0: [{"name": "River", "type": "waterway:river"}]}
        mocker.patch("services.rag_service.neo4j_service.get_cached_pois_for_waypoints",
                     return_value=cached)
        mock_osm = mocker.patch("services.rag_service.osm_client.query_pois_for_waypoints")

        result = svc._fetch_poi_map(WAYPOINTS)

        assert result == cached
        mock_osm.assert_not_called()

    def test_cache_miss_calls_osm_and_stores(self, rag_svc, mocker):
        svc, _ = rag_svc
        fetched = {0: [{"name": "River", "type": "waterway:river"}]}
        mocker.patch("services.rag_service.neo4j_service.get_cached_pois_for_waypoints",
                     return_value=None)
        mock_osm = mocker.patch("services.rag_service.osm_client.query_pois_for_waypoints",
                                return_value=fetched)
        mock_store = mocker.patch("services.rag_service.neo4j_service.store_pois_for_waypoints")

        result = svc._fetch_poi_map(WAYPOINTS)

        mock_osm.assert_called_once()
        mock_store.assert_called_once_with(WAYPOINTS, fetched)
        assert result == fetched


# ===========================================================================
# _fetch_elevations
# ===========================================================================

class TestFetchElevations:

    def test_cache_hit_returns_cached_elevations(self, rag_svc, mocker):
        svc, _ = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_cached_elevations_for_waypoints",
                     return_value=ELEVATIONS)
        mock_api = mocker.patch("services.rag_service.elevation_client.get_elevations")

        result = svc._fetch_elevations(WAYPOINTS)

        assert result == ELEVATIONS
        mock_api.assert_not_called()

    def test_cache_miss_calls_api_and_stores(self, rag_svc, mocker):
        svc, _ = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_cached_elevations_for_waypoints",
                     return_value=None)
        mock_api = mocker.patch("services.rag_service.elevation_client.get_elevations",
                                return_value=ELEVATIONS)
        mock_store = mocker.patch("services.rag_service.neo4j_service.store_elevations_for_waypoints")

        result = svc._fetch_elevations(WAYPOINTS)

        mock_api.assert_called_once_with(WAYPOINTS)
        mock_store.assert_called_once_with(WAYPOINTS, ELEVATIONS)
        assert result == ELEVATIONS


# ===========================================================================
# build_context
# ===========================================================================

class TestBuildContext:

    def test_route_not_found_returns_none(self, rag_svc, mocker):
        svc, _ = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_route", return_value=None)

        route, waypoints, poi_map, elevations = svc.build_context("nonexistent-id")

        assert route is None
        assert waypoints == []

    def test_no_waypoints_returns_empty_collections(self, rag_svc, mocker):
        svc, _ = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_route", return_value={"id": "r1", "name": "Test"})
        mocker.patch("services.rag_service.neo4j_service.get_waypoints", return_value=[])

        route, waypoints, poi_map, elevations = svc.build_context("r1")

        assert route is not None
        assert waypoints == []
        assert poi_map == {}
        assert elevations == []

    def test_full_context_returns_route_waypoints_pois_elevations(self, rag_svc, mocker):
        svc, _ = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_route",
                     return_value={"id": "r1", "name": "Test Route"})
        mocker.patch("services.rag_service.neo4j_service.get_waypoints", return_value=WAYPOINTS)
        mocker.patch("services.rag_service.neo4j_service.get_cached_pois_for_waypoints",
                     return_value=POI_MAP)
        mocker.patch("services.rag_service.neo4j_service.get_cached_elevations_for_waypoints",
                     return_value=ELEVATIONS)

        route, waypoints, poi_map, elevations = svc.build_context("r1")

        assert route["name"] == "Test Route"
        assert waypoints == WAYPOINTS
        assert poi_map == POI_MAP
        assert elevations == ELEVATIONS


# ===========================================================================
# _generate_meta_prompt
# ===========================================================================

class TestGenerateMetaPrompt:

    def test_no_notes_returns_default_system_prompt(self, rag_svc, mocker):
        svc, llm = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_waypoints",
                     return_value=[{"text_note": None}, {"text_note": ""}])

        result = svc._generate_meta_prompt("r1", llm)
        assert result == svc.system_prompt

    def test_uses_at_most_three_notes(self, rag_svc, mocker):
        svc, llm = rag_svc
        wps = [{"text_note": f"note {i}"} for i in range(6)]
        mocker.patch("services.rag_service.neo4j_service.get_waypoints", return_value=wps)
        llm.invoke.return_value = "[SYSTEM_PROMPT]\nYou are a custom narrator."

        svc._generate_meta_prompt("r1", llm)
        prompt_text = llm.invoke.call_args.args[0]
        # Only notes 0-2 should appear, not note 3
        assert "note 0" in prompt_text
        assert "note 2" in prompt_text
        assert "note 3" not in prompt_text

    def test_valid_llm_response_extracts_system_prompt(self, rag_svc, mocker):
        svc, llm = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_waypoints",
                     return_value=[{"text_note": "We walked along the river."}])
        llm.invoke.return_value = (
            "[ANALYSIS]\nSentences are medium length.\n\n"
            "[SYSTEM_PROMPT]\nYou are a walk narrator. Write one paragraph per waypoint."
        )

        result = svc._generate_meta_prompt("r1", llm)
        assert result == "You are a walk narrator. Write one paragraph per waypoint."

    def test_llm_exception_returns_default_system_prompt(self, rag_svc, mocker):
        svc, llm = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_waypoints",
                     return_value=[{"text_note": "A note."}])
        llm.invoke.side_effect = RuntimeError("connection refused")

        result = svc._generate_meta_prompt("r1", llm)
        assert result == svc.system_prompt

    def test_llm_response_too_short_returns_default_system_prompt(self, rag_svc, mocker):
        svc, llm = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_waypoints",
                     return_value=[{"text_note": "A note."}])
        llm.invoke.return_value = "[SYSTEM_PROMPT]\nOK"  # under 50 chars

        result = svc._generate_meta_prompt("r1", llm)
        assert result == svc.system_prompt


# ===========================================================================
# generate_travelogue
# ===========================================================================

class TestGenerateTravelogue:

    def _patch_full_pipeline(self, mocker, route=None, waypoints=None, poi_map=None, elevations=None):
        """Convenience: patch all data-layer calls and LLM chain."""
        mocker.patch("services.rag_service.neo4j_service.get_route",
                     return_value=route or {"id": "r1", "name": "Test"})
        mocker.patch("services.rag_service.neo4j_service.get_waypoints",
                     return_value=waypoints or WAYPOINTS)
        mocker.patch("services.rag_service.neo4j_service.get_cached_pois_for_waypoints",
                     return_value=poi_map or POI_MAP)
        mocker.patch("services.rag_service.neo4j_service.get_cached_elevations_for_waypoints",
                     return_value=elevations or ELEVATIONS)

    def test_route_not_found_returns_error_text(self, rag_svc, mocker):
        svc, _ = rag_svc
        mocker.patch("services.rag_service.neo4j_service.get_route", return_value=None)

        result = svc.generate_travelogue("bad-id")
        assert "Route not found" in result["text"]
        assert result["meta_prompted"] is False

    def test_result_contains_expected_keys(self, rag_svc, mocker):
        svc, _ = rag_svc
        self._patch_full_pipeline(mocker)

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Para 1.\n\nPara 2.\n\nPara 3."
        mocker.patch("services.rag_service.ChatPromptTemplate.from_messages",
                     return_value=MagicMock(__or__=MagicMock(
                         return_value=MagicMock(__or__=MagicMock(return_value=mock_chain))
                     )))
        # Bypass salience ranking
        mocker.patch.object(svc, "_rank_pois_salience", side_effect=lambda m, _: m)

        result = svc.generate_travelogue("r1")
        assert {"text", "llm_model", "prompt_type", "meta_prompted"} == set(result.keys())

    def test_meta_prompted_false_when_not_requested(self, rag_svc, mocker):
        svc, _ = rag_svc
        self._patch_full_pipeline(mocker)
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Generated text."
        mocker.patch("services.rag_service.ChatPromptTemplate.from_messages",
                     return_value=MagicMock(__or__=MagicMock(
                         return_value=MagicMock(__or__=MagicMock(return_value=mock_chain))
                     )))
        mocker.patch.object(svc, "_rank_pois_salience", side_effect=lambda m, _: m)

        result = svc.generate_travelogue("r1", use_meta_prompt=False)
        assert result["meta_prompted"] is False

    def test_meta_prompted_true_calls_generate_meta_prompt(self, rag_svc, mocker):
        svc, _ = rag_svc
        self._patch_full_pipeline(mocker)
        mock_meta = mocker.patch.object(svc, "_generate_meta_prompt",
                                        return_value="Custom system prompt.")
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Generated text."
        mocker.patch("services.rag_service.ChatPromptTemplate.from_messages",
                     return_value=MagicMock(__or__=MagicMock(
                         return_value=MagicMock(__or__=MagicMock(return_value=mock_chain))
                     )))
        mocker.patch.object(svc, "_rank_pois_salience", side_effect=lambda m, _: m)

        result = svc.generate_travelogue("r1", use_meta_prompt=True)
        mock_meta.assert_called_once()
        assert result["meta_prompted"] is True

    def test_llm_exception_returns_error_in_text(self, rag_svc, mocker):
        svc, _ = rag_svc
        self._patch_full_pipeline(mocker)
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = RuntimeError("Ollama timeout")
        mocker.patch("services.rag_service.ChatPromptTemplate.from_messages",
                     return_value=MagicMock(__or__=MagicMock(
                         return_value=MagicMock(__or__=MagicMock(return_value=mock_chain))
                     )))
        mocker.patch.object(svc, "_rank_pois_salience", side_effect=lambda m, _: m)

        result = svc.generate_travelogue("r1")
        assert "Generation failed" in result["text"]
        assert result["meta_prompted"] is False

    def test_prompt_type_zero_shot_stored_in_result(self, rag_svc, mocker):
        svc, _ = rag_svc
        self._patch_full_pipeline(mocker)
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "text"
        mocker.patch("services.rag_service.ChatPromptTemplate.from_messages",
                     return_value=MagicMock(__or__=MagicMock(
                         return_value=MagicMock(__or__=MagicMock(return_value=mock_chain))
                     )))
        mocker.patch.object(svc, "_rank_pois_salience", side_effect=lambda m, _: m)

        result = svc.generate_travelogue("r1", prompt_type="zero_shot")
        assert result["prompt_type"] == "zero_shot"
