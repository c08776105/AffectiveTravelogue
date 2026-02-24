import time

import requests

from utils.config import settings
from utils.logger import logger


class OSMClient:
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"

    def query_pois(self, latitude, longitude, radius=500):
        """
        Query Overpass API for POIs around a coordinate
        """
        query = f"""
        [out:json][timeout:{settings.OPENSTREETMAP_API_TIMEOUT}];
        (
          node["amenity"](around:{radius},{latitude},{longitude});
          node["leisure"](around:{radius},{latitude},{longitude});
          node["natural"](around:{radius},{latitude},{longitude});
          node["tourism"](around:{radius},{latitude},{longitude});
          node["historic"](around:{radius},{latitude},{longitude});
        );
        out body;
        """

        print(query)  # Temporarily print query for testing on Overpass Turbo

        retries = 3
        for i in range(retries):
            try:
                response = requests.post(
                    self.overpass_url,
                    data={"data": query},
                    timeout=settings.OPENSTREETMAP_API_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()

                pois = []
                for element in data.get("elements", []):
                    tags = element.get("tags", {})
                    name = tags.get("name", "Unnamed POI")
                    poi_type = (
                        tags.get("amenity")
                        or tags.get("leisure")
                        or tags.get("natural")
                        or tags.get("tourism")
                        or tags.get("historic")
                    )
                    pois.append({"name": name, "type": poi_type})

                return pois
            except Exception as e:
                logger.error(f"OSM Query failed (attempt {i + 1}): {e}")
                if i < retries - 1:
                    time.sleep(2**i)  # Exponential backoff
                else:
                    return []
        return []


osm_client = OSMClient()
