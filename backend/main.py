from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import routes, waypoints, generate, evaluate
from utils.config import settings
from utils.logger import logger

app = FastAPI(
    title="Affective Travelogue API",
    description="Backend for MSc Dissertation project on AI-synthesised travelogues",
    version="1.0.0"
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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "affective-travelogue-backend"}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Affective Travelogue Backend...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Affective Travelogue Backend...")
