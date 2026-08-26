from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.scheme import GovernmentScheme
from app.schemas.scheme import SchemeMatchRequest, MatchedSchemeResult, GovernmentSchemeRead
from app.services.scheme_engine import SchemeEligibilityEngine

router = APIRouter(prefix="/schemes", tags=["Government Schemes & Subsidies"])


@router.get("/", response_model=List[GovernmentSchemeRead])
async def list_government_schemes(db: AsyncSession = Depends(get_db)) -> Any:
    """List all available government concessional credit & subsidy schemes."""
    res = await db.execute(select(GovernmentScheme).where(GovernmentScheme.is_active == True))
    schemes = res.scalars().all()
    if not schemes:
        # Fallback to in-memory schemes database if DB is unseeded
        return [
            GovernmentSchemeRead(
                id=f"scheme-{i}",
                scheme_code=s["scheme_code"],
                name_en=s["scheme_name"],
                name_te=s["scheme_name"],
                name_hi=s["scheme_name"],
                nodal_agency=s["nodal_agency"],
                min_project_cost=s["min_cost"],
                max_project_cost=s["max_cost"],
                general_margin_pct=s["general_margin_pct"],
                special_margin_pct=s["special_margin_pct"],
                general_subsidy_rural_pct=s["general_rural_subsidy"],
                general_subsidy_urban_pct=s["general_urban_subsidy"],
                special_subsidy_rural_pct=s["special_rural_subsidy"],
                special_subsidy_urban_pct=s["special_urban_subsidy"],
                max_subsidy_amount=s["max_subsidy_cap"],
                default_annual_interest_rate=s["interest_rate"],
                interest_subvention_pct=2.0,
                max_tenure_months=60,
                eligible_sectors=s["eligible_sectors"],
                eligible_categories=s["eligible_categories"],
                is_active=True
            )
            for i, s in enumerate(SchemeEligibilityEngine.SCHEMES_DATABASE)
        ]
    return schemes


@router.post("/match", response_model=List[MatchedSchemeResult])
async def match_schemes(
    request: SchemeMatchRequest
) -> Any:
    """
    Evaluate eligibility and calculate subsidy amounts across PMEGP, Mudra, PMFME, and Stand-Up India.
    """
    return SchemeEligibilityEngine.evaluate_eligibility(
        sector_code=request.sector_code,
        project_cost=request.project_cost,
        user_margin_available=request.user_margin_available,
        category=request.category,
        is_rural=request.is_rural,
        applicant_age=request.applicant_age,
        education_level=request.education_level
    )

