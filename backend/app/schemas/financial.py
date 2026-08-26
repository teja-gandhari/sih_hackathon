from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
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


class QuarterlyRepaymentEntry(BaseModel):
    quarter_number: int
    is_moratorium: bool
    principal_repayment: float
    interest_payment: float
    total_installment: float
    closing_balance: float


class SmartStructuringRequest(BaseModel):
    available_margin_capital: float = Field(..., gt=0, description="Available Margin Capital in INR (must be > 0)")
    business_category: Optional[str] = "dairy"
    category: Optional[SocialCategoryEnum] = SocialCategoryEnum.GENERAL
    is_rural: bool = True
    location_district: Optional[str] = "Nalgonda"


class SmartStructuringResponse(BaseModel):
    eligible: bool
    selected_scheme_tier: Optional[str] = None  # "Micro Finance Scheme" or "Term Loan Scheme"
    scheme_code: Optional[str] = None  # "SCA_MICRO_FINANCE" or "SCA_TERM_LOAN"
    nodal_agency: Optional[str] = None
    ineligibility_reason: Optional[str] = None
    
    available_margin_capital: float
    margin_percentage: float = 10.0
    total_feasible_project_cost: float
    maximum_loan_amount: Optional[float] = None
    
    # Scheme details (None when ineligible)
    concessional_interest_rate_pct: Optional[float] = None
    loan_tenure_years: Optional[int] = None
    loan_tenure_months: Optional[int] = None
    moratorium_months: Optional[int] = None
    
    # Repayment & Schedules (None / empty when ineligible)
    monthly_emi_amount: Optional[float] = None
    quarterly_installment_amount: Optional[float] = None
    quarterly_repayment_schedule: List[QuarterlyRepaymentEntry] = []
    
    # Working Capital & Roadmap
    working_capital_buffer_recommended: Optional[float] = None
    operational_cost_guidance: Optional[Dict[str, Any]] = None
    financial_roadmap_summary: str



