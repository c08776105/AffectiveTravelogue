from fastapi import APIRouter, HTTPException
from models.waypoint import WaypointCreate, WaypointResponse
from services.neo4j_service import neo4j_service
from utils.logger import logger

router = APIRouter(prefix="/api/waypoints", tags=["Waypoints"])

@router.post("/", response_model=WaypointResponse, status_code=201)
async def submit_waypoint(waypoint: WaypointCreate):
    try:
        node = neo4j_service.store_waypoint(waypoint)
        return dict(node)
    except Exception as e:
        logger.error(f"Failed to submit waypoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
