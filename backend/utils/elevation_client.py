import time

import requests

from utils.config import settings
from utils.logger import logger


class ElevationClient:
    """
    Batch elevation lookup via the Open-Elevation REST API.
    Returns metres above sea level for a list of waypoints.
    Falls back to None per-waypoint on failure so callers degrade gracefully.
    """

    RETRY_DELAYS = [5, 15, 30]

    def get_elevations(self, waypoints: list[dict]) -> list[float | None]:
        """
        Return a list of elevation values (metres) aligned with the input
        waypoints list.  Any waypoint that cannot be resolved returns None.
        """
        if not waypoints:
            return []

        locations = [
            {"latitude": wp["latitude"], "longitude": wp["longitude"]}
            for wp in waypoints
        ]

        max_attempts = len(self.RETRY_DELAYS) + 1
        for attempt in range(max_attempts):
            try:
                response = requests.post(
                    settings.ELEVATION_API_URL,
                    json={"locations": locations},
                    timeout=settings.ELEVATION_API_TIMEOUT,
                )

                if response.status_code in (429, 503):
                    delay = int(
                        response.headers.get(
                            "Retry-After",
                            self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)],
                        )
                    )
                    logger.warning(
                        f"Elevation API rate limited (HTTP {response.status_code}). "
                        f"Waiting {delay}s (attempt {attempt + 1}/{max_attempts})"
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                results = response.json().get("results", [])
                elevations = [
                    float(r["elevation"]) if r.get("elevation") is not None else None
                    for r in results
                ]

                if len(elevations) != len(waypoints):
                    logger.warning(
                        f"Elevation API returned {len(elevations)} results for "
                        f"{len(waypoints)} waypoints, padding with None"
                    )
                    elevations += [None] * (len(waypoints) - len(elevations))

                logger.info(
                    f"Elevation fetched for {len(waypoints)} waypoints"
                )
                return elevations

            except requests.exceptions.HTTPError as e:
                logger.error(f"Elevation API HTTP error (attempt {attempt + 1}): {e}")
            except Exception as e:
                logger.error(f"Elevation API error (attempt {attempt + 1}): {e}")

            if attempt < max_attempts - 1:
                delay = self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)]
                logger.info(f"Retrying elevation API in {delay}s…")
                time.sleep(delay)

        logger.warning("Elevation API exhausted all retries, proceeding without elevation data")
        return [None] * len(waypoints)


elevation_client = ElevationClient()
