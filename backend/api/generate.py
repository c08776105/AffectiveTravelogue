from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.route import TravelogueCreate, TravelogueResponse
from services.neo4j_service import neo4j_service
from services.rag_service import rag_service
from utils.config import settings

router = APIRouter(prefix="/api/generate", tags=["Generation"])


@router.get("/models")
async def list_models():
    """Return the names of models available in the configured Ollama instance."""
    try:
        response = requests.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=5.0)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        return {"models": models, "default": settings.LLM_MODEL}
    except Exception:
        return {"models": [], "default": settings.LLM_MODEL}


@router.post("/{route_id}", response_model=TravelogueResponse)
async def generate_travelogue(route_id: str, body: Optional[TravelogueCreate] = None):
    if not neo4j_service.get_route(route_id):
        raise HTTPException(status_code=404, detail="Route not found")

    llm_model = body.llm_model if body else None
    prompt_type = body.prompt_type if body else "zero_shot"
    use_meta_prompt = body.use_meta_prompt if body else False

    try:
        result = rag_service.generate_travelogue(
            route_id,
            llm_model=llm_model,
            prompt_type=prompt_type,
            use_meta_prompt=use_meta_prompt,
        )
        node = neo4j_service.store_travelogue_node(
            route_id,
            result["text"],
            result["llm_model"],
            result["prompt_type"],
            meta_prompted=result.get("meta_prompted", False),
        )
        return node
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{route_id}", response_model=list[TravelogueResponse])
async def list_travelogues(route_id: str):
    if not neo4j_service.get_route(route_id):
        raise HTTPException(status_code=404, detail="Route not found")
    return neo4j_service.get_travelogues(route_id)
