from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class VillageRead(BaseModel):
    id: str
    sub_district_id: str
    village_name: str
    pincode: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SubDistrictRead(BaseModel):
    id: str
    district_id: str
    sub_district_name: str
    villages: Optional[List[VillageRead]] = None

    model_config = ConfigDict(from_attributes=True)


class DistrictRead(BaseModel):
    id: str
    state_name: str
    district_name: str
    state_code: str
    sub_districts: Optional[List[SubDistrictRead]] = None

    model_config = ConfigDict(from_attributes=True)


class MarketDataRead(BaseModel):
    id: str
    district_id: str
    sub_district_id: Optional[str] = None
    sector_code: str
    demand_index: float
    formal_competitor_count: int
    estimated_informal_competitor_count: int
    mgnrega_daily_wage_rate: float
    average_monthly_household_income: float
    purchasing_power_tier: str
    seasonal_dependence: str
    harvest_months: List[str]
    nearest_mandi_distance_km: float
    raw_material_availability_score: float
    infrastructure_score: float
    regional_cluster_density_25km: float
    regional_cluster_failure_rate_pct: float
    data_confidence_level: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MarketDataCreate(BaseModel):
    district_id: str
    sub_district_id: Optional[str] = None
    sector_code: str
    demand_index: float = 7.5
    formal_competitor_count: int = 2
    estimated_informal_competitor_count: int = 4
    mgnrega_daily_wage_rate: float = 300.0
    average_monthly_household_income: float = 14000.0
    purchasing_power_tier: str = "lower_middle"
    seasonal_dependence: str = "heavy_agri_cyclical"
    harvest_months: List[str] = ["Oct", "Nov", "Dec", "Apr", "May"]
    nearest_mandi_distance_km: float = 8.5
    raw_material_availability_score: float = 8.0
    infrastructure_score: float = 7.0
    regional_cluster_density_25km: float = 5.0
    regional_cluster_failure_rate_pct: float = 15.0
    data_confidence_level: str = "moderate_proxy"
    notes: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Hyper-Local Market Demand, Competition and Business Viability Schemas
# ─────────────────────────────────────────────────────────────────────────────

class LocationCoordinates(BaseModel):
    latitude: float
    longitude: float


class LocationDetails(BaseModel):
    village: str
    block: Optional[str] = None
    district: str
    state: str = "Telangana"
    coordinates: Optional[LocationCoordinates] = None


class PopulationAnalysisResult(BaseModel):
    village_population: Optional[int] = None
    reachable_population: Optional[int] = None
    population_source: str
    is_estimated: bool = False
    retrieved_at: Optional[datetime] = None


class CompetitionAnalysisResult(BaseModel):
    existing_competitor_count: int
    competitor_names: List[str] = []
    competition_level: str  # "LOW", "MODERATE", "HIGH"
    competitor_source: str  # "OpenStreetMap Overpass API", "Local Registry", "Seeded Demo Data"
    population_per_existing_competitor: Optional[float] = None
    projected_population_per_business: Optional[float] = None


class MarketCapacityAnalysisResult(BaseModel):
    recommended_population_per_business: float
    estimated_market_capacity: int
    existing_businesses: int
    capacity_gap: int
    market_saturation_percentage: float


class MarketOpportunityResult(BaseModel):
    score: float  # 0 to 100
    classification: str  # "HIGH_OPPORTUNITY", "MODERATE_OPPORTUNITY", "LOW_OPPORTUNITY", "HIGH_SATURATION_HIGH_RISK"
    demand_capacity_score: float
    competition_gap_score: float
    reachable_population_score: float
    market_reach_score: float
    reasoning: List[str] = []


class MarketRecommendationResult(BaseModel):
    should_proceed: bool
    recommendation_level: str  # "PROCEED", "REVIEW", "HIGH_RISK"
    summary: str
    key_reasons: List[str] = []


class DataQualityResult(BaseModel):
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    sources: List[str] = []
    limitations: List[str] = []


class MarketAnalysisRequest(BaseModel):
    village: Optional[str] = "Village A"
    block: Optional[str] = None
    district: str = "Nalgonda"
    state: str = "Telangana"
    business_category: str = "kirana"  # kirana, dairy, food_processing, retail, textiles, etc.
    business_type_id: Optional[str] = None
    radius_km: float = 5.0
    village_population: Optional[int] = None  # Optional user override/fallback


class MarketAnalysisResponse(BaseModel):
    location: LocationDetails
    business_category: str
    analysis_radius_km: float
    population_analysis: PopulationAnalysisResult
    competition_analysis: CompetitionAnalysisResult
    market_capacity_analysis: MarketCapacityAnalysisResult
    market_opportunity: MarketOpportunityResult
    recommendation: MarketRecommendationResult
    data_quality: DataQualityResult

    model_config = ConfigDict(from_attributes=True)


