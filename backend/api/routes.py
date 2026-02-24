from fastapi import APIRouter, HTTPException

from models.route import RouteCreate, RouteResponse, RouteUpdate
from services.neo4j_service import neo4j_service

router = APIRouter(prefix="/api/routes", tags=["Routes"])


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


@router.delete("/{id}")
async def delete_route(id: str):
    return {"message": "Delete logic not fully implemented", "id": id}
