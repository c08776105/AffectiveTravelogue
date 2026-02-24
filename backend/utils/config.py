import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Neo4j configuration
    NEO4J_URI: str = "neo4j+s://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # Ollama host configuration
    OLLAMA_HOST: str = "http://localhost:11434"

    # AI Models
    LLM_MODEL: str = "llama3.1:8b"
    BERTSCORE_MODEL: str = "roberta-large"

    # API configuration
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:8000"]

    # External APIs
    OPENSTREETMAP_API_TIMEOUT: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
