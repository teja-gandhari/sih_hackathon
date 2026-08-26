from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.financial import FinancialBreakdownResponse
from app.schemas.scheme import MatchedSchemeResult


class SWOTAnalysis(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]


class FeasibilityBreakdownResponse(BaseModel):
    application_id: str
    overall_score: float  # 0 to 100
    market_demand_score: float
    financial_viability_score: float
    purchasing_power_fit_score: float
    resource_readiness_score: float
    risk_score: float
    
    viability_rating: str  # high_feasibility, moderate_feasibility, high_risk, not_recommended
    market_gap_classification: str  # viable_and_unserved, niche_weekly_market, unviable_purchasing_power_gap, saturated_informal_market
    
    # Deep Rural Market Risk Warnings
    informal_competition_warning: Optional[str] = None
    seasonal_cashflow_warning: Optional[str] = None
    regional_cluster_signal: Optional[str] = None
    data_confidence_level: str
    
    matched_schemes: List[MatchedSchemeResult]
    financial_summary: Optional[FinancialBreakdownResponse] = None
    swot_analysis: Optional[SWOTAnalysis] = None
    localized_advisory: Dict[str, str] = {}  # "en", "te", "hi"
    voice_script: Dict[str, str] = {}
    key_recommendations: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class AdvisoryQueryRequest(BaseModel):
    query_text: str
    language: str = "te"  # te, hi, en
    application_id: Optional[str] = None
    # If no application_id, user can pass transient params
    business_sector: Optional[str] = "dairy"
    scale_units: Optional[int] = 5
    available_margin: Optional[float] = 50000.0
    location_district: Optional[str] = "Nalgonda"


class AdvisoryQueryResponse(BaseModel):
    query_text: str
    language: str
    conversational_response: str
    audio_tts_text: str
    feasibility_score: float
    viability_rating: str
    market_gap_flag: str
    recommended_scheme: str
    estimated_subsidy: float
    estimated_loan: float
    estimated_monthly_emi: float
    key_risks_and_mitigation: List[str]
    swot: SWOTAnalysis

