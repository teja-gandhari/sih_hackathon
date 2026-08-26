from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.feasibility import (
    FeasibilityAnalyzeRequest,
    UnifiedFeasibilityAnalyzeResponse
)
from app.services.feasibility_engine import FeasibilityScoringEngine

router = APIRouter(prefix="/feasibility", tags=["Unified Feasibility Engine"])


@router.post("/analyze", response_model=UnifiedFeasibilityAnalyzeResponse)
async def analyze_unified_feasibility(
    request: FeasibilityAnalyzeRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Unified Multi-Pillar Deterministic Feasibility Engine.
    
    Collects and synthesizes:
    1. Financial Feasibility Engine (40% weight)
    2. Hyper-Local Market Demand & Viability Engine (40% weight)
    3. Government Scheme & Loan Suitability (10% weight)
    4. Ground Risk & Saturation Factors (10% weight)
    
    Returns:
    - overall_feasibility_score (0 - 100)
    - classification (HIGHLY_FEASIBLE / FEASIBLE / MODERATE / HIGH_RISK)
    - component scores (financial, market, scheme, risk)
    - explainable strengths, weaknesses, opportunities, key risks
    - deterministic explanation
    """
    return await FeasibilityScoringEngine.analyze_unified_feasibility(
        db=db,
        request=request
    )

