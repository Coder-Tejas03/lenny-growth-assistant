"""
Lenny Growth Assistant — FastAPI Application Entry Point

Configures ASGI middleware, CORS, structured request logging,
custom exception handlers, and modular API routers.
"""

from typing import Dict
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.api.artifacts import router as artifacts_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import RequestContextMiddleware

# Initialize FastAPI application
app = FastAPI(
    title="Lenny Growth Assistant API",
    description="Grounded AI assistant powered by Lenny's Podcast transcripts",
    version="0.1.0",
)

# 1. Register custom exception handlers (standard structured error envelope)
register_exception_handlers(app)

# 2. Add Request ID & Structured Logging Middleware
app.add_middleware(RequestContextMiddleware)

# 3. Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Include Routers
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(artifacts_router)



@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """Root endpoint verifying API availability."""
    return {
        "service": "Lenny Growth Assistant API",
        "status": "healthy",
        "version": "0.1.0",
    }
