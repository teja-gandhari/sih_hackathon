from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class BusinessProfileSummary(BaseModel):
    business_category: str
    location: Dict[str, str]  # village, block, district, state
    available_margin_capital: float

class FinancialSummaryDetails(BaseModel):
    project_cost: float
    loan_amount: float
    interest_rate: float
    loan_tenure_years: int
    moratorium_months: int
    monthly_emi: float
    quarterly_installment: float

class SchemeSummaryDetails(BaseModel):
    scheme_name: str
    eligible: bool
    maximum_loan: float

class MarketSummaryDetails(BaseModel):
    reachable_population: int
    competitor_count: int
    competition_level: str
    market_saturation_percentage: float
    market_opportunity_score: float
    market_classification: str

class FeasibilitySummaryDetails(BaseModel):
    overall_score: float
    classification: str
    financial_score: float
    market_score: float
    scheme_score: float
    risk_score: float

class DataQualityDetails(BaseModel):
    overall_confidence: str
    sources_used: List[str]
    limitations: List[str]

class FinalReportSummary(BaseModel):
    application_id: str
    business_profile: BusinessProfileSummary
    financial_summary: Optional[FinancialSummaryDetails] = None
    scheme_summary: Optional[SchemeSummaryDetails] = None
    market_summary: Optional[MarketSummaryDetails] = None
    feasibility_summary: Optional[FeasibilitySummaryDetails] = None
    
    key_opportunities: List[str] = []
    key_risks: List[str] = []
    recommendation: Dict[str, Any] = {}
    
    data_quality: DataQualityDetails
    ai_advisory: Optional[str] = None  # If any exists

    model_config = ConfigDict(from_attributes=True)

