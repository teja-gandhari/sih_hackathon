from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.user import SocialCategoryEnum


class FinancialCalculateRequest(BaseModel):
    capex: float
    monthly_opex: float
    monthly_revenue: float
    working_capital_months: int = 3
    user_margin_available: float = 50000.0
    scheme_code: str = "PMEGP"
    category: SocialCategoryEnum = SocialCategoryEnum.GENERAL
    is_rural: bool = True
    loan_tenure_months: int = 60
    annual_interest_rate: float = 8.5
    has_seasonal_dip: bool = False


class FinancialBreakdownResponse(BaseModel):
    total_capex: float
    total_opex_monthly: float
    working_capital_buffer: float
    total_project_cost: float
    
    user_margin_amount: float
    user_margin_pct: float
    subsidy_amount_eligible: float
    subsidy_pct: float
    matched_scheme_code: str
    
    net_bank_loan_required: float
    loan_tenure_months: int
    annual_interest_rate: float
    monthly_emi_amount: float
    
    projected_monthly_revenue: float
    monthly_gross_profit: float
    monthly_net_profit: float
    break_even_months: float
    dscr_ratio: float
    is_bankable: bool  # True if DSCR >= 1.4
    roi_percentage: float
    payback_period_years: float
    
    cash_flow_5yr: Dict[str, Any]
    cost_breakdown: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class FinancialPlanRead(FinancialBreakdownResponse):
    id: str
    application_id: str
    created_at: datetime

