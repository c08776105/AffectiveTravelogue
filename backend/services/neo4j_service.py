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
                created_at=datetime.utcnow(),
            )
            return self._format_node(result.single()["r"])

    def get_route(self, route_id: str):
        with self.driver.session() as session:
            query = "MATCH (r:Route {id: $id}) RETURN r"
            result = session.run(query, id=route_id)
            record = result.single()
            return self._format_node(record["r"]) if record else None

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
                created_at=datetime.utcnow(),
            )
            return self._format_node(result.single()["e"])

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
