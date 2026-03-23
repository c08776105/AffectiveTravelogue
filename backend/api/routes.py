from fastapi import APIRouter, HTTPException

from models.route import RouteCreate, RouteResponse, RouteUpdate
from models.waypoint import WaypointResponse
from services.neo4j_service import neo4j_service

router = APIRouter(prefix="/api/routes", tags=["Routes"])


@router.get("/", response_model=list[RouteResponse])
async def list_routes():
    try:
        routes = neo4j_service.get_all_routes()
        return [dict(route) for route in routes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=RouteResponse, status_code=201)
async def create_route(route: RouteCreate):
    try:
        node = neo4j_service.create_route(route)
        return dict(node)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}", response_model=RouteResponse)
async def get_route(id: str):
    node = neo4j_service.get_route(id)
    if not node:
        raise HTTPException(status_code=404, detail="Route not found")
    return dict(node)


@router.patch("/{id}", response_model=RouteResponse)
async def update_route(id: str, update: RouteUpdate):
    # This acts both as a patch and the finalise endpoint for the MVP
    # Ideally, we would update the Neo4j route node with properties
    node = neo4j_service.update_route(id, update)
    if not node:
        raise HTTPException(status_code=404, detail="Route not found")
    return dict(node)


@router.post("/{id}/finalise", response_model=RouteResponse)
async def finalise_route(id: str, update: RouteUpdate):
    node = neo4j_service.update_route(id, update)
    if not node:
        raise HTTPException(status_code=404, detail="Route not found")
    return dict(node)


@router.get("/{id}/waypoints", response_model=list[WaypointResponse])
async def get_route_waypoints(id: str):
    route = neo4j_service.get_route(id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    waypoints = neo4j_service.get_waypoints(id)
    return [dict(w) for w in waypoints]


@router.delete("/{id}", status_code=204)
async def delete_route(id: str):
    deleted = neo4j_service.delete_route(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Route not found")
