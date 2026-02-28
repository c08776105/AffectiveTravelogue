from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import evaluate, generate, routes, waypoints
from services.neo4j_service import neo4j_service
from services.rag_service import rag_service
from utils.config import settings
from utils.logger import logger

app = FastAPI(
    title="Affective Travelogue API",
    description="Backend for MSc Dissertation project on AI-synthesised travelogues",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router)
app.include_router(waypoints.router)
app.include_router(generate.router)
app.include_router(evaluate.router)


@app.get("/api/health")
async def health_check():
    neo4j_status = neo4j_service.neo4j_service_accessible()
    llm_accessible = rag_service.llm_accessible()
    return {
        "status": "healthy",
        "service": "affective-travelogue-backend",
        "neo4j": neo4j_status,
        "llm": llm_accessible,
    }


@app.get("/api/heartbeat")
async def heartbeat():
    return {}


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Affective Travelogue Backend...")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Affective Travelogue Backend...")
