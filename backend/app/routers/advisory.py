from typing import Any, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.business import BusinessType
from app.models.application import BusinessApplication
from app.schemas.feasibility import AdvisoryQueryRequest, AdvisoryQueryResponse
from app.schemas.voice import VoiceAdvisoryResponse
from app.services.financial_engine import FinancialCalculationEngine
from app.services.scheme_engine import SchemeEligibilityEngine
from app.services.market_service import MarketService
from app.services.feasibility_engine import FeasibilityScoringEngine
from app.services.ai_service import GeminiAIService
from app.services.voice_service import VoiceService
from app.routers.users import get_current_user

router = APIRouter(prefix="/advisory", tags=["Multilingual AI Advisory & Voice"])


async def _aggregate_advisory_context(
    db: AsyncSession,
    user: User,
    business_sector: str = "dairy",
    scale_units: int = 5,
    available_margin: float = 50000.0,
    application_id: Optional[str] = None
) -> dict:
    """Helper that collects full grounded parameters for Gemini AI."""
    sector_clean = business_sector.lower() if business_sector else "dairy"
    margin = available_margin if available_margin > 0 else user.available_margin_money

    # 1. Benchmarks & Scale
    if application_id:
        res = await db.execute(
            select(BusinessApplication)
            .options(selectinload(BusinessApplication.business_type))
            .where(BusinessApplication.id == application_id)
        )
        app_obj = res.scalars().first()
        if app_obj and app_obj.business_type:
            bt = app_obj.business_type
            scale = app_obj.scale_units
            margin = app_obj.user_margin_available
        else:
            scale = scale_units
    else:
        scale = scale_units

    sector_benchmarks = {
        "dairy": {"capex": 350000.0, "opex": 22000.0, "rev": 38000.0, "name": "Dairy Farming (5 Murrah Buffaloes)"},
        "food_processing": {"capex": 280000.0, "opex": 25000.0, "rev": 45000.0, "name": "Spice Grinding & Flour Mill"},
        "retail": {"capex": 200000.0, "opex": 15000.0, "rev": 32000.0, "name": "Village Kirana & FMCG Store"},
        "agriculture": {"capex": 180000.0, "opex": 12000.0, "rev": 26000.0, "name": "Commercial Vermicompost Unit"},
        "textiles": {"capex": 160000.0, "opex": 14000.0, "rev": 28000.0, "name": "Multi-Machine Tailoring Center"},
        "handicrafts": {"capex": 140000.0, "opex": 11000.0, "rev": 24000.0, "name": "Jute & Artisan Craft Unit"},
        "services": {"capex": 175000.0, "opex": 12000.0, "rev": 27000.0, "name": "CSC Digital & Electronics Repair"}
    }
    b_data = sector_benchmarks.get(sector_clean, sector_benchmarks["dairy"])

    financials = FinancialCalculationEngine.compute_full_financial_plan(
        capex=b_data["capex"],
        monthly_opex=b_data["opex"],
        monthly_revenue=b_data["rev"],
        user_margin_available=margin,
        category=user.social_category,
        is_rural=True
    )

    schemes = SchemeEligibilityEngine.evaluate_eligibility(
        sector_code=sector_clean,
        project_cost=financials.total_project_cost,
        user_margin_available=margin,
        category=user.social_category,
        is_rural=True
    )
    top_scheme = schemes[0] if schemes else None

    market_data = await MarketService.get_market_indicators(
        db=db,
        sector_code=sector_clean
    )

    feasibility = FeasibilityScoringEngine.evaluate_feasibility(
        application_id=application_id or "demo-app",
        financials=financials,
        matched_schemes=schemes,
        market_data=market_data,
        business_type={"name_en": b_data["name"], "typical_ticket_size": 45.0, "is_export_or_wholesale": True}
    )

    return {
        "user_profile": {
            "name": user.full_name,
            "category": user.social_category.value,
            "preferred_language": user.preferred_language.value,
            "available_margin": margin,
            "location": f"{user.village}, {user.district}, {user.state}"
        },
        "business": {
            "name": b_data["name"],
            "sector": sector_clean,
            "scale": scale
        },
        "financials": financials.model_dump(),
        "top_scheme": top_scheme.model_dump() if top_scheme else {},
        "market_data": market_data,
        "feasibility": feasibility.model_dump()
    }


@router.post("/query", response_model=AdvisoryQueryResponse)
async def query_ai_advisor(
    request: AdvisoryQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Multilingual text interaction with RuralBiz AI Assistant (in Telugu, Hindi, or English).
    Takes a question like 'Is dairy business suitable for me?' and returns a fully grounded advisory.
    """
    context = await _aggregate_advisory_context(
        db=db,
        user=current_user,
        business_sector=request.business_sector or "dairy",
        scale_units=request.scale_units or 5,
        available_margin=request.available_margin or current_user.available_margin_money,
        application_id=request.application_id
    )

    return await GeminiAIService.generate_advisory(
        query_text=request.query_text,
        language=request.language or current_user.preferred_language.value,
        context_data=context
    )


@router.post("/voice-query", response_model=VoiceAdvisoryResponse)
async def query_voice_advisor(
    audio_file: UploadFile = File(...),
    business_sector: Optional[str] = Form("dairy"),
    language_hint: Optional[str] = Form("te"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Voice-enabled query endpoint for Flutter mobile app.
    Uploads audio, transcribes speech in Telugu/Hindi/English, and returns audio-ready TTS advisory.
    """
    context = await _aggregate_advisory_context(
        db=db,
        user=current_user,
        business_sector=business_sector or "dairy"
    )

    return await VoiceService.process_voice_query(
        audio_file=audio_file,
        context_data=context,
        language_hint=language_hint or current_user.preferred_language.value
    )


@router.post("/chat")
async def chat_with_ai_advisor(
    request: "AdvisoryChatRequest",
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    AI Business Advisor Chat Endpoint.
    
    Accepts a user question about their business and returns a grounded AI response
    based on real Financial Engine, Market Engine, and Feasibility Engine data.
    
    Supports:
    - en (English)
    - te (Telugu తెలుగు)
    - hi (Hindi हिंदी)
    
    The AI advisor:
    - Uses ONLY backend-calculated data (never invents numbers)
    - Explains and advises based on the actual feasibility analysis
    - Falls back to deterministic grounded responses if AI API is unavailable
    """
    from app.schemas.feasibility import AdvisoryChatRequest as ChatReq
    # Validate request type
    if not isinstance(request, ChatReq):
        request = ChatReq(**request.model_dump() if hasattr(request, "model_dump") else request)
    
    return await GeminiAIService.generate_chat_advisory(
        db=db,
        request=request,
    )


@router.get("/context/{application_id}")
async def get_advisory_context(
    application_id: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Returns the structured context that would be provided to the AI advisor.
    
    The frontend can inspect this to see exactly what data the AI receives.
    No AI is called — this is purely the grounded backend data.
    """
    from app.schemas.feasibility import AdvisoryChatRequest
    
    # Build a minimal request from the application_id
    req = AdvisoryChatRequest(
        application_id=application_id,
        question="context-only",
        language="en"
    )
    context = await GeminiAIService.build_advisory_context(db=db, request=req)
    return context


# Import the chat request schema at module level for FastAPI to resolve
from app.schemas.feasibility import AdvisoryChatRequest  # noqa: E402

