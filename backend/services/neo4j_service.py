import uuid
from datetime import datetime

import neo4j.time
from neo4j import GraphDatabase

from utils.config import settings
from utils.logger import logger


class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def _format_node(self, node):
        if not node:
            return None
        formatted = dict(node)
        for key, value in formatted.items():
            if isinstance(value, neo4j.time.DateTime):
                formatted[key] = value.to_native()
        return formatted

    def create_route(self, route_data):
        with self.driver.session() as session:
            route_id = str(uuid.uuid4())
            query = """
            CREATE (r:Route {
                id: $id,
                name: $name,
                start_lat: $start_lat,
                start_lon: $start_lon,
                end_lat: $end_lat,
                end_lon: $end_lon,
                distance_km: $distance_km,
                derive_points: $derive_points,
                deviation_meters: $deviation_meters,
                created_at: $created_at,
                status: 'active'
            })
            RETURN r
            """
            result = session.run(
                query,
                id=route_id,
                name=route_data.name,
                start_lat=route_data.start_lat,
                start_lon=route_data.start_lon,
                end_lat=route_data.end_lat,
                end_lon=route_data.end_lon,
                distance_km=route_data.distance_km,
                derive_points=route_data.derive_points,
                deviation_meters=route_data.deviation_meters,
                created_at=datetime.utcnow(),
            )
            return self._format_node(result.single()["r"])

    def get_route(self, route_id: str):
        with self.driver.session() as session:
            query = "MATCH (r:Route {id: $id}) RETURN r"
            result = session.run(query, id=route_id)
            record = result.single()
            return self._format_node(record["r"]) if record else None

    def get_all_routes(self):
        with self.driver.session() as session:
            query = """
            MATCH (r:Route) WHERE r.status = 'completed'
            OPTIONAL MATCH (r)-[:HAS_WAYPOINT]->(w:Waypoint)
            WITH r, count(w) AS waypoint_count,
                 head([wp IN collect(w) WHERE wp.text_note IS NOT NULL AND wp.text_note <> '' | wp.text_note]) AS first_note
            RETURN r, waypoint_count, first_note ORDER BY r.created_at ASC
            """
            result = session.run(query)
            rows = []
            for record in result:
                node = self._format_node(record["r"])
                node["waypoint_count"] = record["waypoint_count"]
                node["first_note"] = record["first_note"]
                logger.debug(f"Route {node.get('id')}: waypoint_count={node['waypoint_count']}, first_note={repr(node['first_note'])}")
                rows.append(node)
            return rows

    def update_route(self, route_id: str, update_data):
        with self.driver.session() as session:
            # Build dynamic SET clause based on the input field data
            update_fields = update_data.model_dump(exclude_unset=True)
            if not update_fields:
                return self.get_route(route_id)

            set_clauses = ", ".join([f"r.{k} = ${k}" for k in update_fields.keys()])
            query = f"MATCH (r:Route {{id: $id}}) SET {set_clauses} RETURN r"

            params = {"id": route_id, **update_fields}
            result = session.run(query, **params)
            record = result.single()
            return self._format_node(record["r"]) if record else None

    def store_waypoint(self, waypoint_data):
        with self.driver.session() as session:
            wp_id = str(uuid.uuid4())
            query = """
            MATCH (r:Route {id: $route_id})
            CREATE (w:Waypoint {
                id: $id,
                latitude: $latitude,
                longitude: $longitude,
                text_note: $text_note,
                voice_blob_url: $voice_blob_url,
                image_url: $image_url,
                stored_at: $stored_at
            })
            CREATE (r)-[:HAS_WAYPOINT]->(w)
            RETURN w
            """
            result = session.run(
                query,
                route_id=waypoint_data.route_id,
                id=wp_id,
                latitude=waypoint_data.latitude,
                longitude=waypoint_data.longitude,
                text_note=waypoint_data.text_note,
                voice_blob_url=waypoint_data.voice_blob_url,
                image_url=waypoint_data.image_url,
                stored_at=datetime.utcnow(),
            )
            return self._format_node(result.single()["w"])

    def get_waypoints(self, route_id: str):
        with self.driver.session() as session:
            query = """
            MATCH (r:Route {id: $id})-[:HAS_WAYPOINT]->(w:Waypoint)
            RETURN w ORDER BY w.stored_at
            """
            result = session.run(query, id=route_id)
            return [self._format_node(record["w"]) for record in result]

    def delete_route(self, route_id: str) -> bool:
        """Delete a route and all its connected nodes (waypoints, evaluations, travelogues)."""
        with self.driver.session() as session:
            query = """
            MATCH (r:Route {id: $id})
            OPTIONAL MATCH (r)-[:HAS_WAYPOINT]->(w:Waypoint)
            OPTIONAL MATCH (r)-[:HAS_EVALUATION]->(e_legacy:Evaluation)
            OPTIONAL MATCH (r)-[:HAS_TRAVELOGUE]->(t:Travelogue)
            OPTIONAL MATCH (t)-[:HAS_EVALUATION]->(e:Evaluation)
            DETACH DELETE r, w, e_legacy, t, e
            RETURN count(r) AS deleted
            """
            result = session.run(query, id=route_id)
            record = result.single()
            return record and record["deleted"] > 0

    def store_travelogue(self, route_id: str, travelogue: str):
        with self.driver.session() as session:
            query = "MATCH (r:Route {id: $id}) SET r.travelogue = $travelogue RETURN r"
            result = session.run(query, id=route_id, travelogue=travelogue)
            record = result.single()
            return self._format_node(record["r"]) if record else None

    def store_evaluation(self, route_id: str, evaluation_data: dict):
        with self.driver.session() as session:
            query = """
            MATCH (r:Route {id: $route_id})
            CREATE (e:Evaluation {
                bertscore_f1: $bertscore_f1,
                bertscore_precision: $bertscore_precision,
                bertscore_recall: $bertscore_recall,
                is_equivalent: $is_equivalent,
                human_sentiment: $human_sentiment,
                ai_sentiment: $ai_sentiment,
                human_journal: $human_journal,
                ai_travelogue: $ai_travelogue,
                created_at: $created_at
            })
            CREATE (r)-[:HAS_EVALUATION]->(e)
            RETURN e
            """
            result = session.run(
                query,
                route_id=route_id,
                bertscore_f1=evaluation_data["bertscore_f1"],
                bertscore_precision=evaluation_data["bertscore_precision"],
                bertscore_recall=evaluation_data["bertscore_recall"],
                is_equivalent=evaluation_data["is_equivalent"],
                human_sentiment=evaluation_data["human_sentiment"],
                ai_sentiment=evaluation_data["ai_sentiment"],
                human_journal=evaluation_data.get("human_journal", ""),
                ai_travelogue=evaluation_data.get("ai_travelogue", ""),
                created_at=datetime.utcnow(),
            )
            return self._format_node(result.single()["e"])

    def delete_evaluation(self, route_id: str) -> None:
        """Delete all Evaluation nodes attached to a route."""
        with self.driver.session() as session:
            query = """
            MATCH (r:Route {id: $id})-[:HAS_EVALUATION]->(e:Evaluation)
            DETACH DELETE e
            """
            session.run(query, id=route_id)

    def get_evaluation(self, route_id: str):
        with self.driver.session() as session:
            query = """
            MATCH (r:Route {id: $id})-[:HAS_EVALUATION]->(e:Evaluation)
            RETURN e ORDER BY e.created_at DESC LIMIT 1
            """
            result = session.run(query, id=route_id)
            record = result.single()
            return self._format_node(record["e"]) if record else None

    def store_elevations_for_waypoints(self, waypoints: list[dict], elevations: list[float | None]) -> None:
        """Cache elevation (metres) on each Waypoint node."""
        if not waypoints:
            return
        with self.driver.session() as session:
            for wp, elev in zip(waypoints, elevations):
                if elev is not None:
                    session.run(
                        "MATCH (w:Waypoint {id: $id}) SET w.elevation_m = $elev",
                        id=wp["id"],
                        elev=elev,
                    )

    def get_cached_elevations_for_waypoints(self, waypoints: list[dict]) -> list[float | None] | None:
        """
        Return cached elevation values aligned with the waypoints list.
        Returns None if any waypoint is missing elevation data (cache miss).
        """
        if not waypoints:
            return []
        ids = [wp["id"] for wp in waypoints]
        with self.driver.session() as session:
            records = session.run(
                "MATCH (w:Waypoint) WHERE w.id IN $ids RETURN w.id AS id, w.elevation_m AS elev",
                ids=ids,
            )
            elev_by_id = {r["id"]: r["elev"] for r in records}

        result = []
        for wp in waypoints:
            elev = elev_by_id.get(wp["id"])
            if elev is None:
                return None  # Cache miss
            result.append(float(elev))
        return result

    def store_pois_for_waypoints(self, waypoints: list[dict], poi_map: dict[int, list[dict]]) -> None:
        """Cache OSM POI results on each Waypoint node to avoid redundant API calls."""
        import json
        if not waypoints:
            return
        with self.driver.session() as session:
            for i, wp in enumerate(waypoints):
                pois = poi_map.get(i, [])
                session.run(
                    "MATCH (w:Waypoint {id: $id}) SET w.poi_cache = $cache, w.poi_fetched_at = $ts",
                    id=wp["id"],
                    cache=json.dumps(pois),
                    ts=datetime.utcnow(),
                )

    def get_cached_pois_for_waypoints(self, waypoints: list[dict]) -> dict[int, list[dict]] | None:
        """Return cached POI data keyed by waypoint index, or None if any waypoint is uncached."""
        import json
        if not waypoints:
            return {}
        ids = [wp["id"] for wp in waypoints]
        with self.driver.session() as session:
            records = session.run(
                "MATCH (w:Waypoint) WHERE w.id IN $ids RETURN w.id AS id, w.poi_cache AS cache",
                ids=ids,
            )
            cache_by_id = {r["id"]: r["cache"] for r in records}

        result = {}
        for i, wp in enumerate(waypoints):
            cache = cache_by_id.get(wp["id"])
            if cache is None:
                return None  # Cache miss — fall back to OSM
            result[i] = json.loads(cache)
        return result

    def get_example_for_few_shot(self, exclude_route_id: str):
        """Fetch the first 3 noted waypoints (oldest first) from a different completed route for few-shot prompting."""
        with self.driver.session() as session:
            query = """
            MATCH (r:Route {status: 'completed'})
            WHERE r.id <> $exclude_id
            MATCH (r)-[:HAS_WAYPOINT]->(w:Waypoint)
            WHERE w.text_note IS NOT NULL AND w.text_note <> ''
            WITH r, w ORDER BY r.created_at DESC, w.stored_at ASC
            WITH r, collect(w)[0..3] AS waypoints
            WHERE size(waypoints) > 0
            RETURN r.name AS route_name, waypoints
            LIMIT 1
            """
            result = session.run(query, exclude_id=exclude_route_id)
            record = result.single()
            if not record:
                return None
            return {
                "route_name": record["route_name"],
                "waypoints": [self._format_node(w) for w in record["waypoints"]],
            }

    def store_travelogue_node(self, route_id: str, text: str, llm_model: str, prompt_type: str = "zero_shot", meta_prompted: bool = False) -> dict:
        with self.driver.session() as session:
            travelogue_id = str(uuid.uuid4())
            query = """
            MATCH (r:Route {id: $route_id})
            CREATE (t:Travelogue {id: $id, text: $text, llm_model: $llm_model, prompt_type: $prompt_type, meta_prompted: $meta_prompted, created_at: $created_at})
            CREATE (r)-[:HAS_TRAVELOGUE]->(t)
            SET r.travelogue = $text
            RETURN t
            """
            result = session.run(
                query,
                route_id=route_id,
                id=travelogue_id,
                text=text,
                llm_model=llm_model,
                prompt_type=prompt_type,
                meta_prompted=meta_prompted,
                created_at=datetime.utcnow(),
            )
            return self._format_node(result.single()["t"])

    def get_travelogues(self, route_id: str) -> list:
        with self.driver.session() as session:
            query = """
            MATCH (r:Route {id: $route_id})-[:HAS_TRAVELOGUE]->(t:Travelogue)
            OPTIONAL MATCH (t)-[:HAS_EVALUATION]->(e:Evaluation)
            RETURN t, e ORDER BY t.created_at DESC
            """
            result = session.run(query, route_id=route_id)
            rows = []
            for record in result:
                node = self._format_node(record["t"])
                node["evaluation"] = self._format_node(record["e"])
                rows.append(node)
            return rows

    def get_travelogue(self, travelogue_id: str):
        with self.driver.session() as session:
            query = """
            MATCH (t:Travelogue {id: $id})
            OPTIONAL MATCH (t)-[:HAS_EVALUATION]->(e:Evaluation)
            RETURN t, e
            """
            result = session.run(query, id=travelogue_id)
            record = result.single()
            if not record:
                return None
            node = self._format_node(record["t"])
            node["evaluation"] = self._format_node(record["e"])
            return node

    def store_evaluation_for_travelogue(self, travelogue_id: str, evaluation_data: dict) -> dict:
        with self.driver.session() as session:
            query = """
            MATCH (t:Travelogue {id: $travelogue_id})
            CREATE (e:Evaluation {
                bertscore_f1: $bertscore_f1,
                bertscore_precision: $bertscore_precision,
                bertscore_recall: $bertscore_recall,
                is_equivalent: $is_equivalent,
                human_sentiment: $human_sentiment,
                ai_sentiment: $ai_sentiment,
                human_journal: $human_journal,
                ai_travelogue: $ai_travelogue,
                bertscore_model: $bertscore_model,
                travelogue_id: $travelogue_id,
                prompt_type: $prompt_type,
                is_truncated: $is_truncated,
                pair_f1: $pair_f1,
                pair_precision: $pair_precision,
                pair_recall: $pair_recall,
                pair_is_truncated: $pair_is_truncated,
                human_waypoint_count: $human_waypoint_count,
                ai_paragraph_count: $ai_paragraph_count,
                created_at: $created_at
            })
            CREATE (t)-[:HAS_EVALUATION]->(e)
            RETURN e
            """
            result = session.run(
                query,
                travelogue_id=travelogue_id,
                bertscore_f1=evaluation_data["bertscore_f1"],
                bertscore_precision=evaluation_data["bertscore_precision"],
                bertscore_recall=evaluation_data["bertscore_recall"],
                is_equivalent=evaluation_data["is_equivalent"],
                human_sentiment=evaluation_data["human_sentiment"],
                ai_sentiment=evaluation_data["ai_sentiment"],
                human_journal=evaluation_data.get("human_journal", ""),
                ai_travelogue=evaluation_data.get("ai_travelogue", ""),
                bertscore_model=evaluation_data.get("bertscore_model", ""),
                prompt_type=evaluation_data.get("prompt_type", "zero_shot"),
                is_truncated=evaluation_data.get("is_truncated", False),
                pair_f1=evaluation_data.get("pair_f1", []),
                pair_precision=evaluation_data.get("pair_precision", []),
                pair_recall=evaluation_data.get("pair_recall", []),
                pair_is_truncated=evaluation_data.get("pair_is_truncated", []),
                human_waypoint_count=evaluation_data.get("human_waypoint_count"),
                ai_paragraph_count=evaluation_data.get("ai_paragraph_count"),
                created_at=datetime.utcnow(),
            )
            return self._format_node(result.single()["e"])

    def get_evaluation_for_travelogue(self, travelogue_id: str):
        with self.driver.session() as session:
            query = """
            MATCH (t:Travelogue {id: $travelogue_id})-[:HAS_EVALUATION]->(e:Evaluation)
            RETURN e ORDER BY e.created_at DESC LIMIT 1
            """
            result = session.run(query, travelogue_id=travelogue_id)
            record = result.single()
            return self._format_node(record["e"]) if record else None

    def delete_evaluation_for_travelogue(self, travelogue_id: str) -> None:
        with self.driver.session() as session:
            query = """
            MATCH (t:Travelogue {id: $travelogue_id})-[:HAS_EVALUATION]->(e:Evaluation)
            DETACH DELETE e
            """
            session.run(query, travelogue_id=travelogue_id)

    def get_evaluation_stats(self) -> dict | None:
        """Return the singleton EvaluationStats node, or None if it doesn't exist yet."""
        with self.driver.session() as session:
            query = """
            MATCH (s:EvaluationStats {id: 'global'})
            RETURN s
            """
            record = session.run(query).single()
            return self._format_node(record["s"]) if record else None

    def update_evaluation_stats(self) -> dict | None:
        """Recompute mean/min/max F1 from valid evaluations and upsert the stats node.

        A valid evaluation is one where:
          - the parent Travelogue has is_valid = true
          - human_waypoint_count equals ai_paragraph_count (counts are non-null and match)

        Returns the upserted stats dict, or None if no valid evaluations exist yet.
        """
        with self.driver.session() as session:
            aggregate_query = """
            MATCH (t:Travelogue)-[:HAS_EVALUATION]->(e:Evaluation)
            WHERE t.is_valid = true
              AND e.human_waypoint_count IS NOT NULL
              AND e.ai_paragraph_count IS NOT NULL
              AND e.human_waypoint_count = e.ai_paragraph_count
            RETURN
                avg(e.bertscore_f1) AS mean_f1,
                min(e.bertscore_f1) AS min_f1,
                max(e.bertscore_f1) AS max_f1,
                count(e)            AS sample_count
            """
            agg = session.run(aggregate_query).single()
            if not agg or agg["sample_count"] == 0:
                return None

            upsert_query = """
            MERGE (s:EvaluationStats {id: 'global'})
            SET s.mean_f1      = $mean_f1,
                s.min_f1       = $min_f1,
                s.max_f1       = $max_f1,
                s.sample_count = $sample_count,
                s.updated_at   = $updated_at
            RETURN s
            """
            from datetime import datetime, timezone
            params = {
                "mean_f1": agg["mean_f1"],
                "min_f1": agg["min_f1"],
                "max_f1": agg["max_f1"],
                "sample_count": agg["sample_count"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            record = session.run(upsert_query, **params).single()
            return self._format_node(record["s"]) if record else None

    def neo4j_service_accessible(self) -> str:
        try:
            with self.driver.session() as session:
                query = "RETURN 1 AS heartbeat"
                result = session.run(query)
                record = result.single()
                if record and record["heartbeat"] == 1:
                    return "up"
                return "down"
        except Exception as e:
            logger.error(f"Neo4j connectivity failed: {e}")
            return "down"


neo4j_service = Neo4jService()
