from fastapi import APIRouter, HTTPException
from services.rag_service import rag_service
from services.neo4j_service import neo4j_service

router = APIRouter(prefix="/api/generate", tags=["Generation"])

@router.post("/{route_id}")
async def generate_travelogue(route_id: str):
    # Check if route exists
    route = neo4j_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
        
    try:
        travelogue = rag_service.generate_travelogue(route_id)
        return {
            "route_id": route_id,
            "status": "completed",
            "travelogue": travelogue
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
