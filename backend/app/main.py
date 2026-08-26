import os
import sys

# Ensure backend directory is always in sys.path regardless of where uvicorn is launched
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import (
    users,
    businesses,
    financial,
    schemes,
    market,
    analysis,
    advisory
)
from app.seeds.schemes import seed_sectors_and_schemes
from app.seeds.market_data import seed_market_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ruralbiz_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event: create tables and seed default benchmark data on startup."""
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Seeding initial benchmark data...")
    try:
        await seed_sectors_and_schemes()
        await seed_market_data()
        logger.info("Database initialized and seeded successfully.")
    except Exception as e:
        logger.warning(f"Auto-seed exception (likely already seeded): {e}")

    yield
    logger.info("Shutting down RuralBiz AI Backend...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Driven Hyper-Local Business Advisory and Financial Feasibility Platform for Rural Entrepreneurs.",
    lifespan=lifespan
)

# CORS middleware for Flutter mobile app integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(businesses.router, prefix=settings.API_V1_STR)
app.include_router(financial.router, prefix=settings.API_V1_STR)
app.include_router(schemes.router, prefix=settings.API_V1_STR)
app.include_router(market.router, prefix=settings.API_V1_STR)
app.include_router(analysis.router, prefix=settings.API_V1_STR)
app.include_router(advisory.router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "supported_languages": ["te", "hi", "en"],
        "docs_url": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}

