from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.business import BusinessType
from app.models.application import BusinessApplication, FinancialPlan
from app.schemas.financial import (
    FinancialCalculateRequest,
    FinancialBreakdownResponse,
    FinancialPlanRead,
    SmartStructuringRequest,
    SmartStructuringResponse
)
from app.services.financial_engine import FinancialCalculationEngine
from app.routers.users import get_current_user

router = APIRouter(prefix="/financial", tags=["Financial Engine"])


@router.post("/smart-structure", response_model=SmartStructuringResponse)
async def smart_financial_structuring_and_scheme_router(
    request: SmartStructuringRequest
) -> Any:
    """
    Module 2: Smart Financial Calculator & Scheme Router.
    Takes Available Margin Capital (e.g. ₹1,00,000) and automatically outputs:
    1. Feasible Project Cost (Margin / 10%)
    2. Maximum Loan Amount (90% of Project Cost)
    3. Scheme Auto-Selection (Micro Finance <= ₹1.40L @ 6.5% vs Term Loan <= ₹50.00L @ 8%)
    4. Quarterly Repayment Schedule with Moratorium grace periods
    """
    return FinancialCalculationEngine.structure_from_available_margin(
        available_margin_capital=request.available_margin_capital,
        business_category=request.business_category or "dairy",
        category=request.category,
        is_rural=request.is_rural,
        location_district=request.location_district or "Nalgonda"
    )



@router.post("/calculate", response_model=FinancialBreakdownResponse)
async def calculate_standalone_financials(
    request: FinancialCalculateRequest
) -> Any:
    """
    Directly compute project cost, margin, subsidy, EMI, DSCR, BEP, and 5-year cash flows.
    """
    return FinancialCalculationEngine.compute_full_financial_plan(
        capex=request.capex,
        monthly_opex=request.monthly_opex,
        monthly_revenue=request.monthly_revenue,
        working_capital_months=request.working_capital_months,
        user_margin_available=request.user_margin_available,
        scheme_code=request.scheme_code,
        category=request.category,
        is_rural=request.is_rural,
        loan_tenure_months=request.loan_tenure_months,
        annual_interest_rate=request.annual_interest_rate,
        has_seasonal_dip=request.has_seasonal_dip
    )


@router.post("/application/{app_id}/calculate", response_model=FinancialBreakdownResponse)
async def calculate_application_financials(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Calculate and persist financial plan for a user's business application.
    """
    res = await db.execute(
        select(BusinessApplication)
        .options(selectinload(BusinessApplication.business_type))
        .where(BusinessApplication.id == app_id, BusinessApplication.user_id == current_user.id)
    )
    application = res.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    bt = application.business_type
    scale_factor = application.scale_units / max(bt.default_scale, 1)

    capex = bt.default_capex * scale_factor
    monthly_opex = bt.default_monthly_opex * scale_factor
    monthly_revenue = bt.default_monthly_revenue * scale_factor

    plan = FinancialCalculationEngine.compute_full_financial_plan(
        capex=capex,
        monthly_opex=monthly_opex,
        monthly_revenue=monthly_revenue,
        user_margin_available=application.user_margin_available,
        category=current_user.social_category,
        is_rural=True,
        has_seasonal_dip=bt.seasonal_cyclical
    )

    # Save or update FinancialPlan in database
    res_plan = await db.execute(select(FinancialPlan).where(FinancialPlan.application_id == app_id))
    fin_plan_db = res_plan.scalars().first()
    if not fin_plan_db:
        fin_plan_db = FinancialPlan(application_id=app_id)
        db.add(fin_plan_db)

    fin_plan_db.total_capex = plan.total_capex
    fin_plan_db.total_opex_monthly = plan.total_opex_monthly
    fin_plan_db.working_capital_buffer = plan.working_capital_buffer
    fin_plan_db.total_project_cost = plan.total_project_cost
    fin_plan_db.user_margin_amount = plan.user_margin_amount
    fin_plan_db.user_margin_pct = plan.user_margin_pct
    fin_plan_db.subsidy_amount_eligible = plan.subsidy_amount_eligible
    fin_plan_db.subsidy_pct = plan.subsidy_pct
    fin_plan_db.matched_scheme_code = plan.matched_scheme_code
    fin_plan_db.net_bank_loan_required = plan.net_bank_loan_required
    fin_plan_db.loan_tenure_months = plan.loan_tenure_months
    fin_plan_db.annual_interest_rate = plan.annual_interest_rate
    fin_plan_db.monthly_emi_amount = plan.monthly_emi_amount
    fin_plan_db.projected_monthly_revenue = plan.projected_monthly_revenue
    fin_plan_db.monthly_gross_profit = plan.monthly_gross_profit
    fin_plan_db.monthly_net_profit = plan.monthly_net_profit
    fin_plan_db.break_even_months = plan.break_even_months
    fin_plan_db.dscr_ratio = plan.dscr_ratio
    fin_plan_db.roi_percentage = plan.roi_percentage
    fin_plan_db.payback_period_years = plan.payback_period_years
    fin_plan_db.cash_flow_5yr = plan.cash_flow_5yr
    fin_plan_db.cost_breakdown = plan.cost_breakdown

    application.status = "calculated"
    await db.commit()

    return plan


@router.get("/application/{app_id}", response_model=FinancialBreakdownResponse)
async def get_application_financial_plan(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Retrieve saved financial model for an application."""
    res = await db.execute(
        select(FinancialPlan)
        .join(BusinessApplication)
        .where(FinancialPlan.application_id == app_id, BusinessApplication.user_id == current_user.id)
    )
    fin_plan = res.scalars().first()
    if not fin_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial plan not found for this application"
        )
    
    is_bankable = fin_plan.dscr_ratio >= 1.4 and fin_plan.monthly_net_profit > 0
    return FinancialBreakdownResponse(
        total_capex=fin_plan.total_capex,
        total_opex_monthly=fin_plan.total_opex_monthly,
        working_capital_buffer=fin_plan.working_capital_buffer,
        total_project_cost=fin_plan.total_project_cost,
        user_margin_amount=fin_plan.user_margin_amount,
        user_margin_pct=fin_plan.user_margin_pct,
        subsidy_amount_eligible=fin_plan.subsidy_amount_eligible,
        subsidy_pct=fin_plan.subsidy_pct,
        matched_scheme_code=fin_plan.matched_scheme_code,
        net_bank_loan_required=fin_plan.net_bank_loan_required,
        loan_tenure_months=fin_plan.loan_tenure_months,
        annual_interest_rate=fin_plan.annual_interest_rate,
        monthly_emi_amount=fin_plan.monthly_emi_amount,
        projected_monthly_revenue=fin_plan.projected_monthly_revenue,
        monthly_gross_profit=fin_plan.monthly_gross_profit,
        monthly_net_profit=fin_plan.monthly_net_profit,
        break_even_months=fin_plan.break_even_months,
        dscr_ratio=fin_plan.dscr_ratio,
        is_bankable=is_bankable,
        roi_percentage=fin_plan.roi_percentage,
        payback_period_years=fin_plan.payback_period_years,
        cash_flow_5yr=fin_plan.cash_flow_5yr or {},
        cost_breakdown=fin_plan.cost_breakdown or {}
    )

