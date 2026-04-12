"""
Tests for Neo4jService.

The Neo4j driver is replaced by a MagicMock throughout.  Each test
configures the mock session's run().single() / __iter__ as needed.
"""

import json
from unittest.mock import MagicMock, call

import pytest

from tests.conftest import ELEVATIONS, WAYPOINTS, make_session_mock


# ===========================================================================
# POI cache
# ===========================================================================

class TestStorePoisForWaypoints:

    def test_stores_json_and_timestamp_on_each_waypoint(self, neo4j_svc):
        ctx, session = make_session_mock()
        neo4j_svc.driver.session.return_value = ctx

        pois = [{"name": "River", "type": "waterway:river"}]
        neo4j_svc.store_pois_for_waypoints(WAYPOINTS[:1], {0: pois})

        assert session.run.call_count == 1
        call_kwargs = session.run.call_args
        assert call_kwargs.kwargs["id"] == "wp-1"
        assert json.loads(call_kwargs.kwargs["cache"]) == pois

    def test_empty_waypoints_makes_no_db_call(self, neo4j_svc):
        neo4j_svc.store_pois_for_waypoints([], {})
        neo4j_svc.driver.session.assert_not_called()

    def test_multiple_waypoints_each_get_their_own_store(self, neo4j_svc):
        results = [MagicMock(), MagicMock()]
        session = MagicMock()
        session.run.return_value = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = lambda s: session
        ctx.__exit__ = MagicMock(return_value=False)
        neo4j_svc.driver.session.return_value = ctx

        poi_map = {0: [{"name": "A", "type": "t"}], 1: [{"name": "B", "type": "t"}]}
        neo4j_svc.store_pois_for_waypoints(WAYPOINTS[:2], poi_map)

        assert session.run.call_count == 2
        ids_stored = [c.kwargs["id"] for c in session.run.call_args_list]
        assert "wp-1" in ids_stored
        assert "wp-2" in ids_stored


class TestGetCachedPoisForWaypoints:

    def test_cache_hit_returns_dict_keyed_by_index(self, neo4j_svc):
        pois = [{"name": "River", "type": "waterway:river"}]
        records = [
            {"id": "wp-1", "cache": json.dumps(pois)},
            {"id": "wp-2", "cache": json.dumps([])},
        ]
        ctx, _ = make_session_mock(records)
        neo4j_svc.driver.session.return_value = ctx

        result = neo4j_svc.get_cached_pois_for_waypoints(WAYPOINTS[:2])

        assert result is not None
        assert result[0] == pois
        assert result[1] == []

    def test_cache_miss_returns_none_when_waypoint_has_no_cache(self, neo4j_svc):
        # Only one waypoint returned — the second is missing
        records = [{"id": "wp-1", "cache": json.dumps([])}]
        ctx, _ = make_session_mock(records)
        neo4j_svc.driver.session.return_value = ctx

        result = neo4j_svc.get_cached_pois_for_waypoints(WAYPOINTS[:2])
        assert result is None

    def test_empty_waypoints_returns_empty_dict(self, neo4j_svc):
        result = neo4j_svc.get_cached_pois_for_waypoints([])
        assert result == {}

    def test_queries_all_waypoint_ids_in_single_call(self, neo4j_svc):
        records = [
            {"id": "wp-1", "cache": "[]"},
            {"id": "wp-2", "cache": "[]"},
            {"id": "wp-3", "cache": "[]"},
        ]
        ctx, session = make_session_mock(records)
        neo4j_svc.driver.session.return_value = ctx

        neo4j_svc.get_cached_pois_for_waypoints(WAYPOINTS)

        assert session.run.call_count == 1
        ids_arg = session.run.call_args.kwargs["ids"]
        assert set(ids_arg) == {"wp-1", "wp-2", "wp-3"}


# ===========================================================================
# Elevation cache
# ===========================================================================

class TestStoreElevationsForWaypoints:

    def test_stores_elevation_on_each_waypoint(self, neo4j_svc):
        session = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = lambda s: session
        ctx.__exit__ = MagicMock(return_value=False)
        neo4j_svc.driver.session.return_value = ctx

        neo4j_svc.store_elevations_for_waypoints(WAYPOINTS[:2], [45.0, 57.0])

        assert session.run.call_count == 2
        elevs = {c.kwargs["id"]: c.kwargs["elev"] for c in session.run.call_args_list}
        assert elevs["wp-1"] == 45.0
        assert elevs["wp-2"] == 57.0

    def test_none_elevation_skips_that_waypoint(self, neo4j_svc):
        session = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = lambda s: session
        ctx.__exit__ = MagicMock(return_value=False)
        neo4j_svc.driver.session.return_value = ctx

        neo4j_svc.store_elevations_for_waypoints(WAYPOINTS[:2], [None, 57.0])

        # Only waypoint 2 (57.0) should be stored; None is skipped
        assert session.run.call_count == 1
        assert session.run.call_args.kwargs["id"] == "wp-2"

    def test_empty_waypoints_makes_no_db_call(self, neo4j_svc):
        neo4j_svc.store_elevations_for_waypoints([], [])
        neo4j_svc.driver.session.assert_not_called()


class TestGetCachedElevationsForWaypoints:

    def test_cache_hit_returns_float_list(self, neo4j_svc):
        records = [
            {"id": "wp-1", "elev": 45.0},
            {"id": "wp-2", "elev": 57.0},
            {"id": "wp-3", "elev": 50.0},
        ]
        ctx, _ = make_session_mock(records)
        neo4j_svc.driver.session.return_value = ctx

        result = neo4j_svc.get_cached_elevations_for_waypoints(WAYPOINTS)

        assert result == [45.0, 57.0, 50.0]

    def test_cache_miss_returns_none_when_waypoint_missing(self, neo4j_svc):
        # Only one record returned — two waypoints missing
        records = [{"id": "wp-1", "elev": 45.0}]
        ctx, _ = make_session_mock(records)
        neo4j_svc.driver.session.return_value = ctx

        result = neo4j_svc.get_cached_elevations_for_waypoints(WAYPOINTS[:2])
        assert result is None

    def test_empty_waypoints_returns_empty_list(self, neo4j_svc):
        result = neo4j_svc.get_cached_elevations_for_waypoints([])
        assert result == []

    def test_elevation_values_are_floats(self, neo4j_svc):
        records = [
            {"id": "wp-1", "elev": 45},   # int from Neo4j
            {"id": "wp-2", "elev": 57.5},
        ]
        ctx, _ = make_session_mock(records)
        neo4j_svc.driver.session.return_value = ctx

        result = neo4j_svc.get_cached_elevations_for_waypoints(WAYPOINTS[:2])
        assert all(isinstance(v, float) for v in result)


# ===========================================================================
# Route CRUD
# ===========================================================================

class TestGetRoute:

    def test_returns_formatted_node_when_found(self, neo4j_svc):
        record = {"r": MagicMock()}
        record["r"].__iter__ = lambda s: iter({"id": "r1", "name": "Test"}.items())
        record["r"].keys = lambda: ["id", "name"]
        record["r"].__getitem__ = lambda s, k: {"id": "r1", "name": "Test"}[k]

        ctx, session = make_session_mock([record])
        neo4j_svc.driver.session.return_value = ctx
        # Patch _format_node to keep it simple
        neo4j_svc._format_node = lambda n: dict(n)

        session.run.return_value.single.return_value = {"r": {"id": "r1", "name": "Test"}}
        neo4j_svc._format_node = lambda n: n

        result = neo4j_svc.get_route("r1")
        assert result == {"id": "r1", "name": "Test"}

    def test_returns_none_when_not_found(self, neo4j_svc):
        ctx, session = make_session_mock()
        session.run.return_value.single.return_value = None
        neo4j_svc.driver.session.return_value = ctx

        result = neo4j_svc.get_route("missing")
        assert result is None


class TestGetWaypoints:

    def test_returns_list_of_formatted_waypoints(self, neo4j_svc):
        wp1 = {"id": "wp-1", "latitude": 53.249, "longitude": -6.589}
        wp2 = {"id": "wp-2", "latitude": 53.248, "longitude": -6.591}
        records = [{"w": wp1}, {"w": wp2}]

        ctx, session = make_session_mock(records)
        session.run.return_value.__iter__ = lambda s: iter(records)
        neo4j_svc.driver.session.return_value = ctx
        neo4j_svc._format_node = lambda n: n

        result = neo4j_svc.get_waypoints("r1")
        assert len(result) == 2

    def test_returns_empty_list_when_no_waypoints(self, neo4j_svc):
        ctx, session = make_session_mock([])
        session.run.return_value.__iter__ = lambda s: iter([])
        neo4j_svc.driver.session.return_value = ctx
        neo4j_svc._format_node = lambda n: n

        result = neo4j_svc.get_waypoints("r1")
        assert result == []


# ===========================================================================
# Few-shot example retrieval
# ===========================================================================

class TestGetExampleForFewShot:

    def test_returns_none_when_no_matching_route(self, neo4j_svc):
        ctx, session = make_session_mock()
        session.run.return_value.single.return_value = None
        neo4j_svc.driver.session.return_value = ctx

        result = neo4j_svc.get_example_for_few_shot("r1")
        assert result is None

    def test_returns_route_name_and_waypoints_when_found(self, neo4j_svc):
        wp = {"id": "wp-x", "latitude": 53.1, "longitude": -6.5, "text_note": "note"}
        record = {"route_name": "Example Route", "waypoints": [wp]}

        ctx, session = make_session_mock([record])
        session.run.return_value.single.return_value = record
        neo4j_svc.driver.session.return_value = ctx
        neo4j_svc._format_node = lambda n: n

        result = neo4j_svc.get_example_for_few_shot("other-route")

        assert result["route_name"] == "Example Route"
        assert len(result["waypoints"]) == 1

    def test_excludes_the_current_route_id(self, neo4j_svc):
        ctx, session = make_session_mock()
        session.run.return_value.single.return_value = None
        neo4j_svc.driver.session.return_value = ctx

        neo4j_svc.get_example_for_few_shot("current-route-id")

        query_kwargs = session.run.call_args.kwargs
        assert query_kwargs["exclude_id"] == "current-route-id"


# ===========================================================================
# Travelogue storage
# ===========================================================================

class TestStoreTravelogueNode:

    def test_stores_all_fields_including_meta_prompted(self, neo4j_svc):
        travelogue_node = {
            "id": "t-1",
            "text": "Generated text",
            "llm_model": "llama3.1:8b",
            "prompt_type": "few_shot",
            "meta_prompted": True,
        }
        ctx, session = make_session_mock()
        session.run.return_value.single.return_value = {"t": travelogue_node}
        neo4j_svc.driver.session.return_value = ctx
        neo4j_svc._format_node = lambda n: n

        result = neo4j_svc.store_travelogue_node(
            "r1", "Generated text", "llama3.1:8b",
            prompt_type="few_shot", meta_prompted=True
        )

        call_kwargs = session.run.call_args.kwargs
        assert call_kwargs["meta_prompted"] is True
        assert call_kwargs["prompt_type"] == "few_shot"
        assert call_kwargs["text"] == "Generated text"

    def test_meta_prompted_defaults_to_false(self, neo4j_svc):
        ctx, session = make_session_mock()
        session.run.return_value.single.return_value = {"t": {}}
        neo4j_svc.driver.session.return_value = ctx
        neo4j_svc._format_node = lambda n: n

        neo4j_svc.store_travelogue_node("r1", "text", "model")

        call_kwargs = session.run.call_args.kwargs
        assert call_kwargs["meta_prompted"] is False
