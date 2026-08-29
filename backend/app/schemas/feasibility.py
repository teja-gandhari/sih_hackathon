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


class MarketReachAnalysis(BaseModel):
    radius_km: float = 7.5
    estimated_consumer_base: int
    primary_distribution_channels: List[str]
    rural_accessibility_summary: str


class OpportunityAnalysis(BaseModel):
    underserved_niches: List[str]
    demand_supply_gap_description: str
    recommended_value_addition: str


class ThreatsIdentification(BaseModel):
    supply_chain_bottlenecks: List[str]
    seasonal_demand_fluctuations: str
    single_buyer_dependency_risk: str
    mitigation_strategies: List[str]


class CompetitorMapping(BaseModel):
    block_density_per_10k: float
    formal_registered_competitors: int
    estimated_informal_competitors: int
    market_saturation_level: str  # low, moderate, saturated
    unserved_demand_headroom_pct: float


class ProductMarketValuePricing(BaseModel):
    suggested_price_point: float
    unit_label: str
    regional_purchasing_power_tier: str
    mgnrega_daily_wage_benchmark: float
    affordability_tier_fit: str
    optimal_pricing_strategy: str


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
    
    # Module 1: Hyper-Local Strategy Sections
    market_reach: Optional[MarketReachAnalysis] = None
    opportunity_analysis: Optional[OpportunityAnalysis] = None
    threats_identification: Optional[ThreatsIdentification] = None
    competitor_mapping: Optional[CompetitorMapping] = None
    product_market_value: Optional[ProductMarketValuePricing] = None
    
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


# ─────────────────────────────────────────────────────────────────────────────
# Unified Feasibility Engine Schemas (POST /api/v1/feasibility/analyze)
# ─────────────────────────────────────────────────────────────────────────────

class FeasibilityAnalyzeRequest(BaseModel):
    application_id: Optional[str] = None
    business_category: Optional[str] = "dairy"
    business_type_id: Optional[str] = None
    available_margin_capital: Optional[float] = 50000.0
    village: Optional[str] = "Village A"
    block: Optional[str] = None
    district: Optional[str] = "Nalgonda"
    state: Optional[str] = "Telangana"
    category: Optional[str] = "obc"  # social category: general, obc, sc, st, women
    is_rural: Optional[bool] = True
    radius_km: Optional[float] = 5.0
    village_population: Optional[int] = None
    scale_units: Optional[int] = None


class UnifiedFeasibilityAnalyzeResponse(BaseModel):
    overall_feasibility_score: float  # 0 to 100
    classification: str  # HIGHLY_FEASIBLE / FEASIBLE / MODERATE / HIGH_RISK
    financial_score: float
    market_score: float
    scheme_score: float
    risk_score: float
    strengths: List[str] = []
    weaknesses: List[str] = []
    opportunities: List[str] = []
    key_risks: List[str] = []
    deterministic_explanation: str
    financial_summary: Optional[Dict[str, Any]] = None
    market_summary: Optional[Dict[str, Any]] = None
    scheme_summary: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# AI Business Advisor Chat Schemas (POST /api/v1/advisory/chat)
# ─────────────────────────────────────────────────────────────────────────────

class AdvisoryChatRequest(BaseModel):
    """Request for AI-powered business advisory chat."""
    application_id: Optional[str] = None
    question: str
    language: str = "en"  # en, te, hi
    # Transient params when no application_id
    business_category: Optional[str] = "dairy"
    available_margin_capital: Optional[float] = 50000.0
    village: Optional[str] = "Village A"
    district: Optional[str] = "Nalgonda"
    state: Optional[str] = "Telangana"
    category: Optional[str] = "obc"
    is_rural: Optional[bool] = True
    radius_km: Optional[float] = 5.0


class AdvisoryContextUsed(BaseModel):
    financial: bool = False
    market: bool = False
    feasibility: bool = False


class AdvisoryContextResponse(BaseModel):
    """Structured context that is provided to the AI, exposed for frontend inspection."""
    business_category: str
    village: str
    district: str
    state: str
    available_margin_capital: float
    total_project_cost: float
    loan_amount: float
    selected_scheme: str
    interest_rate: float
    monthly_emi: float
    repayment_tenure_months: int
    market_population: Optional[int] = None
    reachable_population: Optional[int] = None
    competitor_count: int = 0
    competition_level: str = "LOW"
    market_saturation_pct: float = 0.0
    market_opportunity_score: float = 0.0
    feasibility_score: float = 0.0
    feasibility_classification: str = "MODERATE"
    financial_strengths: List[str] = []
    financial_risks: List[str] = []
    market_opportunities: List[str] = []
    market_risks: List[str] = []
    dscr_ratio: float = 0.0
    roi_percentage: float = 0.0
    break_even_months: float = 0.0
    monthly_net_profit: float = 0.0


class AdvisoryChatResponse(BaseModel):
    """Response from the AI business advisory chat endpoint."""
    answer: str
    language: str
    context_used: AdvisoryContextUsed = AdvisoryContextUsed()
    context_snapshot: Optional[AdvisoryContextResponse] = None
