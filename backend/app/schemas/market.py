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

