from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.business import BusinessType
from app.models.application import BusinessApplication, FinancialPlan, FeasibilityAssessment
from app.schemas.feasibility import FeasibilityBreakdownResponse, SWOTAnalysis
from app.schemas.financial import FinancialBreakdownResponse
from app.services.financial_engine import FinancialCalculationEngine
from app.services.scheme_engine import SchemeEligibilityEngine
from app.services.market_service import MarketService
from app.services.feasibility_engine import FeasibilityScoringEngine
from app.routers.users import get_current_user

router = APIRouter(prefix="/analysis", tags=["Feasibility & Viability Analysis"])


@router.post("/evaluate/{app_id}", response_model=FeasibilityBreakdownResponse)
async def evaluate_application_feasibility(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Run complete multi-factor feasibility assessment:
    Financials + Scheme Matching + Purchasing Power Fit + Unserved vs Unviable Classification + Grounded SWOT.
    """
    res = await db.execute(
        select(BusinessApplication)
        .options(
            selectinload(BusinessApplication.business_type),
            selectinload(BusinessApplication.financial_plan)
        )
        .where(BusinessApplication.id == app_id, BusinessApplication.user_id == current_user.id)
    )
    application = res.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business application not found"
        )

    bt = application.business_type
    scale_factor = application.scale_units / max(bt.default_scale, 1)

    capex = bt.default_capex * scale_factor
    monthly_opex = bt.default_monthly_opex * scale_factor
    monthly_revenue = bt.default_monthly_revenue * scale_factor

    # 1. Financial Computation
    financials = FinancialCalculationEngine.compute_full_financial_plan(
        capex=capex,
        monthly_opex=monthly_opex,
        monthly_revenue=monthly_revenue,
        user_margin_available=application.user_margin_available,
        category=current_user.social_category,
        is_rural=True,
        has_seasonal_dip=bt.seasonal_cyclical
    )

    # 2. Scheme Matching
    schemes = SchemeEligibilityEngine.evaluate_eligibility(
        sector_code=bt.code.split("_")[0] if "_" in bt.code else "dairy",
        project_cost=financials.total_project_cost,
        user_margin_available=application.user_margin_available,
        category=current_user.social_category,
        is_rural=True,
        education_level=current_user.education_level
    )

    # 3. Market Indicators & Economic Proxies
    market_data = await MarketService.get_market_indicators(
        db=db,
        sector_code=bt.code.split("_")[0] if "_" in bt.code else "dairy",
        district_id=application.district_id,
        sub_district_id=application.sub_district_id
    )

    # 4. Feasibility & Risk Classification
    assessment_result = FeasibilityScoringEngine.evaluate_feasibility(
        application_id=app_id,
        financials=financials,
        matched_schemes=schemes,
        market_data=market_data,
        business_type={
            "name_en": bt.name_en,
            "typical_ticket_size": bt.typical_ticket_size,
            "is_export_or_wholesale": bt.is_export_or_wholesale,
            "requires_daily_footfall": bt.requires_daily_footfall
        }
    )

    # Persist FeasibilityAssessment in DB
    res_fa = await db.execute(select(FeasibilityAssessment).where(FeasibilityAssessment.application_id == app_id))
    fa_db = res_fa.scalars().first()
    if not fa_db:
        fa_db = FeasibilityAssessment(application_id=app_id)
        db.add(fa_db)

    fa_db.overall_score = assessment_result.overall_score
    fa_db.market_demand_score = assessment_result.market_demand_score
    fa_db.financial_viability_score = assessment_result.financial_viability_score
    fa_db.purchasing_power_fit_score = assessment_result.purchasing_power_fit_score
    fa_db.resource_readiness_score = assessment_result.resource_readiness_score
    fa_db.risk_score = assessment_result.risk_score
    fa_db.viability_rating = assessment_result.viability_rating
    fa_db.market_gap_classification = assessment_result.market_gap_classification
    fa_db.informal_competition_warning = assessment_result.informal_competition_warning
    fa_db.seasonal_cashflow_warning = assessment_result.seasonal_cashflow_warning
    fa_db.regional_cluster_signal = assessment_result.regional_cluster_signal
    fa_db.data_confidence_level = assessment_result.data_confidence_level
    fa_db.matched_schemes = [s.model_dump() for s in schemes]
    fa_db.swot_analysis = assessment_result.swot_analysis.model_dump() if assessment_result.swot_analysis else {}
    fa_db.key_recommendations = assessment_result.key_recommendations

    application.status = "evaluated"
    await db.commit()

    return assessment_result


@router.get("/{app_id}", response_model=FeasibilityBreakdownResponse)
async def get_feasibility_assessment(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Retrieve saved feasibility assessment report."""
    res = await db.execute(
        select(FeasibilityAssessment)
        .join(BusinessApplication)
        .where(FeasibilityAssessment.application_id == app_id, BusinessApplication.user_id == current_user.id)
    )
    fa = res.scalars().first()
    if not fa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feasibility assessment not found. Please evaluate first."
        )

    swot = SWOTAnalysis(**fa.swot_analysis) if fa.swot_analysis else None

    return FeasibilityBreakdownResponse(
        application_id=fa.application_id,
        overall_score=fa.overall_score,
        market_demand_score=fa.market_demand_score,
        financial_viability_score=fa.financial_viability_score,
        purchasing_power_fit_score=fa.purchasing_power_fit_score,
        resource_readiness_score=fa.resource_readiness_score,
        risk_score=fa.risk_score,
        viability_rating=fa.viability_rating,
        market_gap_classification=fa.market_gap_classification,
        informal_competition_warning=fa.informal_competition_warning,
        seasonal_cashflow_warning=fa.seasonal_cashflow_warning,
        regional_cluster_signal=fa.regional_cluster_signal,
        data_confidence_level=fa.data_confidence_level or "moderate_proxy",
        matched_schemes=fa.matched_schemes or [],
        swot_analysis=swot,
        localized_advisory=fa.localized_advisory_text or {},
        voice_script=fa.voice_script_text or {},
        key_recommendations=fa.key_recommendations or []
    )


@router.get("/{app_id}/report")
async def generate_bank_pitch_report(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate a full consolidated bank-ready project profile & feasibility report.
    """
    res = await db.execute(
        select(BusinessApplication)
        .options(
            selectinload(BusinessApplication.business_type),
            selectinload(BusinessApplication.financial_plan),
            selectinload(BusinessApplication.feasibility_assessment)
        )
        .where(BusinessApplication.id == app_id, BusinessApplication.user_id == current_user.id)
    )
    app_obj = res.scalars().first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")

    bt = app_obj.business_type
    fp = app_obj.financial_plan
    fa = app_obj.feasibility_assessment

    return {
        "report_title": f"Project Feasibility & Bank Loan Assessment: {bt.name_en}",
        "report_id": f"RB-{app_obj.id[:8].upper()}",
        "entrepreneur_profile": {
            "name": current_user.full_name,
            "phone": current_user.phone_number,
            "category": current_user.social_category,
            "education": current_user.education_level,
            "location": f"{current_user.village}, {current_user.sub_district}, {current_user.district}, {current_user.state}",
            "margin_money_available": f"₹{app_obj.user_margin_available:,.2f}"
        },
        "enterprise_profile": {
            "business_name": bt.name_en,
            "scale": f"{app_obj.scale_units} {bt.unit_label}",
            "land_available": f"{app_obj.land_area_sqft} sqft ({'Owned' if app_obj.own_land_available else 'Rented'})"
        },
        "financial_summary": {
            "total_project_cost": f"₹{fp.total_project_cost:,.2f}" if fp else "N/A",
            "capex": f"₹{fp.total_capex:,.2f}" if fp else "N/A",
            "working_capital_buffer": f"₹{fp.working_capital_buffer:,.2f}" if fp else "N/A",
            "promoter_margin": f"₹{fp.user_margin_amount:,.2f} ({fp.user_margin_pct:.1f}%)" if fp else "N/A",
            "eligible_govt_subsidy": f"₹{fp.subsidy_amount_eligible:,.2f} ({fp.subsidy_pct:.1f}%)" if fp else "N/A",
            "net_bank_loan": f"₹{fp.net_bank_loan_required:,.2f}" if fp else "N/A",
            "monthly_emi": f"₹{fp.monthly_emi_amount:,.2f} (@ {fp.annual_interest_rate}% for {fp.loan_tenure_months} months)" if fp else "N/A",
            "projected_monthly_revenue": f"₹{fp.projected_monthly_revenue:,.2f}" if fp else "N/A",
            "monthly_net_profit": f"₹{fp.monthly_net_profit:,.2f}" if fp else "N/A",
            "dscr_ratio": fp.dscr_ratio if fp else 0.0,
            "break_even_months": fp.break_even_months if fp else 0.0,
            "roi_percentage": f"{fp.roi_percentage:.1f}%" if fp else "N/A"
        },
        "market_and_viability": {
            "feasibility_score": f"{fa.overall_score:.1f}/100" if fa else "N/A",
            "rating": fa.viability_rating if fa else "N/A",
            "market_gap_classification": fa.market_gap_classification if fa else "N/A",
            "informal_competition_warning": fa.informal_competition_warning if fa else "N/A",
            "seasonal_warning": fa.seasonal_cashflow_warning if fa else "N/A",
            "data_confidence": fa.data_confidence_level if fa else "moderate_proxy"
        },
        "swot_analysis": fa.swot_analysis if fa else {},
        "recommendations": fa.key_recommendations if fa else []
    }

