import math
import time

import requests

from utils.config import settings
from utils.logger import logger


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS-84 points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin(math.radians(lat2 - lat1) / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


class OSMClient:
    BASE_URL = "https://overpass-api.de/api/interpreter"
    # Backoff delays (seconds) for 429 / 504 / network errors
    RETRY_DELAYS = [15, 45, 90]

    def query_pois_for_waypoints(
        self, waypoints: list[dict], radius: int = 50
    ) -> dict[int, list[dict]]:
        """
        Fetch POIs for all waypoints in a single Overpass API call.

        Builds one batched union query covering every waypoint × every tag type,
        then associates each returned POI with the waypoint(s) it falls within
        `radius` metres of (using Haversine distance, client-side).

        Returns a dict mapping waypoint index → list of {"name", "type"} dicts.
        Falls back to empty lists for all waypoints if all retries are exhausted.
        """
        if not waypoints:
            return {}

        query_timeout = max(30, settings.OPENSTREETMAP_API_TIMEOUT)

        # Tags queried for every waypoint.
        # nwr = node + way + relation so that area features (forests, rivers,
        # parks, fields, buildings) are included, not just point nodes.
        POI_TAGS = (
            "amenity",
            "leisure",
            "natural",
            "tourism",
            "historic",
            "waterway",
            "landuse",
            "man_made",
            "place",
            "building",
            "railway",
            "boundary",
        )

        clauses = []
        for wp in waypoints:
            lat, lon = wp["latitude"], wp["longitude"]
            for tag in POI_TAGS:
                clauses.append(f'  nwr["{tag}"](around:{radius},{lat},{lon});')

        # "out center" returns a centroid lat/lon for ways and relations
        # so they can be distance-filtered the same way as point nodes.
        query = (
            f"[out:json][timeout:{query_timeout}];\n"
            "(\n"
            + "\n".join(clauses)
            + "\n);\nout center;"
        )

        max_attempts = len(self.RETRY_DELAYS) + 1
        for attempt in range(max_attempts):
            try:
                response = requests.post(
                    self.BASE_URL,
                    data={"data": query},
                    timeout=query_timeout + 10,
                )

                if response.status_code in (429, 504):
                    delay = int(
                        response.headers.get(
                            "Retry-After",
                            self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)],
                        )
                    )
                    logger.warning(
                        f"OSM rate limited (HTTP {response.status_code}). "
                        f"Waiting {delay}s (attempt {attempt + 1}/{max_attempts})"
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                elements = response.json().get("elements", [])

                # Associate each OSM element with every waypoint within radius.
                # Deduplicate per waypoint by OSM node id so overlapping around
                # clauses don't produce duplicate POI entries.
                result: dict[int, list[dict]] = {i: [] for i in range(len(waypoints))}
                seen_per_wp: dict[int, set] = {i: set() for i in range(len(waypoints))}

                for element in elements:
                    # Nodes have direct lat/lon; ways and relations have a
                    # "center" object returned by "out center".
                    poi_lat = element.get("lat") or (element.get("center") or {}).get("lat")
                    poi_lon = element.get("lon") or (element.get("center") or {}).get("lon")
                    if poi_lat is None or poi_lon is None:
                        continue

                    tags = element.get("tags", {})
                    name = tags.get("name", "Unnamed POI")
                    poi_type = (
                        tags.get("amenity")
                        or tags.get("leisure")
                        or tags.get("natural")
                        or tags.get("tourism")
                        or tags.get("historic")
                        or tags.get("waterway")
                        or tags.get("landuse")
                        or tags.get("man_made")
                        or tags.get("place")
                        or tags.get("building")
                        or tags.get("railway")
                        or tags.get("boundary")
                    )
                    osm_id = element.get("id")

                    for i, wp in enumerate(waypoints):
                        if osm_id in seen_per_wp[i]:
                            continue
                        if _haversine_m(wp["latitude"], wp["longitude"], poi_lat, poi_lon) <= radius:
                            result[i].append({"name": name, "type": poi_type})
                            seen_per_wp[i].add(osm_id)

                logger.info(
                    f"OSM batch query: {len(elements)} elements for "
                    f"{len(waypoints)} waypoints (1 API call)"
                )
                return result

            except requests.exceptions.HTTPError as e:
                logger.error(f"OSM query failed (attempt {attempt + 1}): {e}")
            except Exception as e:
                logger.error(f"OSM query error (attempt {attempt + 1}): {e}")

            if attempt < max_attempts - 1:
                delay = self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)]
                logger.info(f"Retrying OSM query in {delay}s…")
                time.sleep(delay)

        logger.warning("OSM query exhausted all retries, proceeding without POI data")
        return {i: [] for i in range(len(waypoints))}

    def query_pois(self, latitude: float, longitude: float, radius: int = 50) -> list[dict]:
        """Single-waypoint convenience wrapper (backwards compatible)."""
        result = self.query_pois_for_waypoints(
            [{"latitude": latitude, "longitude": longitude}], radius
        )
        return result.get(0, [])


osm_client = OSMClient()
