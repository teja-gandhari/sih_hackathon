from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.user import SocialCategoryEnum


class SchemeMatchRequest(BaseModel):
    sector_code: str
    project_cost: float
    user_margin_available: float
    category: SocialCategoryEnum = SocialCategoryEnum.GENERAL
    is_rural: bool = True
    applicant_age: int = 28
    education_level: str = "10th_pass"


class MatchedSchemeResult(BaseModel):
    scheme_code: str
    scheme_name: str
    nodal_agency: str
    eligible: bool
    subsidy_percentage: float
    subsidy_amount: float
    margin_required_percentage: float
    margin_required_amount: float
    net_bank_loan: float
    estimated_interest_rate: float
    reasons: List[str]
    benefits: List[str]


class GovernmentSchemeRead(BaseModel):
    id: str
    scheme_code: str
    name_en: str
    name_te: str
    name_hi: str
    nodal_agency: str
    min_project_cost: float
    max_project_cost: float
    general_margin_pct: float
    special_margin_pct: float
    general_subsidy_rural_pct: float
    general_subsidy_urban_pct: float
    special_subsidy_rural_pct: float
    special_subsidy_urban_pct: float
    max_subsidy_amount: float
    default_annual_interest_rate: float
    interest_subvention_pct: float
    max_tenure_months: int
    eligible_sectors: List[str]
    eligible_categories: List[str]
    description_en: Optional[str] = None
    description_te: Optional[str] = None
    description_hi: Optional[str] = None
    application_portal_url: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

