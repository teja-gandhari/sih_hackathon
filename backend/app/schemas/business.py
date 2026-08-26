from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BusinessSectorRead(BaseModel):
    id: str
    code: str
    name_en: str
    name_te: str
    name_hi: str
    description: Optional[str] = None
    icon_name: str

    model_config = ConfigDict(from_attributes=True)


class BusinessTypeRead(BaseModel):
    id: str
    sector_id: str
    code: str
    name_en: str
    name_te: str
    name_hi: str
    description_en: Optional[str] = None
    description_te: Optional[str] = None
    description_hi: Optional[str] = None
    unit_label: str
    default_scale: int
    default_capex: float
    default_monthly_opex: float
    default_monthly_revenue: float
    typical_ticket_size: float
    min_purchasing_power_tier: str
    requires_daily_footfall: bool
    is_export_or_wholesale: bool
    seasonal_cyclical: bool
    capex_breakdown: Dict[str, Any]
    opex_breakdown: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class ApplicationCreate(BaseModel):
    business_type_id: str
    district_id: Optional[str] = None
    sub_district_id: Optional[str] = None
    village_id: Optional[str] = None
    scale_units: int = 5
    target_price_per_unit: Optional[float] = None
    user_margin_available: float = 50000.0
    own_land_available: bool = True
    land_area_sqft: float = 1000.0
    prior_experience_years: float = 1.0


class ApplicationUpdate(BaseModel):
    scale_units: Optional[int] = None
    target_price_per_unit: Optional[float] = None
    user_margin_available: Optional[float] = None
    own_land_available: Optional[bool] = None
    land_area_sqft: Optional[float] = None
    prior_experience_years: Optional[float] = None
    status: Optional[str] = None


class ApplicationRead(BaseModel):
    id: str
    user_id: str
    business_type_id: str
    district_id: Optional[str] = None
    sub_district_id: Optional[str] = None
    village_id: Optional[str] = None
    scale_units: int
    target_price_per_unit: Optional[float] = None
    user_margin_available: float
    own_land_available: bool
    land_area_sqft: float
    prior_experience_years: float
    status: str
    created_at: datetime
    updated_at: datetime
    business_type: Optional[BusinessTypeRead] = None

    model_config = ConfigDict(from_attributes=True)

