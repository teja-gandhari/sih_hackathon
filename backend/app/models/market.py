import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class District(Base):
    __tablename__ = "districts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    state_name = Column(String(100), nullable=False)
    district_name = Column(String(100), unique=True, index=True, nullable=False)
    state_code = Column(String(10), default="IN-TG")
    population = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Relationships
    sub_districts = relationship("SubDistrict", back_populates="district", cascade="all, delete-orphan")
    market_data = relationship("MarketData", back_populates="district", cascade="all, delete-orphan")


class SubDistrict(Base):
    __tablename__ = "sub_districts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    district_id = Column(String(36), ForeignKey("districts.id"), nullable=False, index=True)
    sub_district_name = Column(String(100), nullable=False, index=True)  # Block / Mandal / Taluk
    population = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Relationships
    district = relationship("District", back_populates="sub_districts")
    villages = relationship("Village", back_populates="sub_district", cascade="all, delete-orphan")
    market_data = relationship("MarketData", back_populates="sub_district", cascade="all, delete-orphan")


class Village(Base):
    __tablename__ = "villages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sub_district_id = Column(String(36), ForeignKey("sub_districts.id"), nullable=False, index=True)
    village_name = Column(String(100), nullable=False, index=True)
    pincode = Column(String(10), nullable=True)
    population = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Relationships
    sub_district = relationship("SubDistrict", back_populates="villages")


class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    district_id = Column(String(36), ForeignKey("districts.id"), nullable=False, index=True)
    sub_district_id = Column(String(36), ForeignKey("sub_districts.id"), nullable=True, index=True)
    sector_code = Column(String(50), nullable=False, index=True)  # dairy, retail, food_processing, etc.
    
    # Core Demand & Competitor Metrics
    demand_index = Column(Float, default=7.5)  # 1.0 - 10.0
    formal_competitor_count = Column(Integer, default=2)
    estimated_informal_competitor_count = Column(Integer, default=4)  # Roadside stalls, cart sellers, unregistered
    
    # Economic & Purchasing Power Proxies (Beyond population)
    mgnrega_daily_wage_rate = Column(Float, default=300.0)  # Daily wage in INR
    average_monthly_household_income = Column(Float, default=14000.0)
    purchasing_power_tier = Column(String(30), default="lower_middle")  # low, lower_middle, middle, high
    
    # Seasonality & Cash Flow Cyclicality
    seasonal_dependence = Column(String(30), default="heavy_agri_cyclical")  # heavy_agri_cyclical, moderate, stable_salaried
    harvest_months = Column(JSON, default=lambda: ["Oct", "Nov", "Dec", "Apr", "May"])
    
    # Supply Chain & Logistics
    nearest_mandi_distance_km = Column(Float, default=8.5)
    raw_material_availability_score = Column(Float, default=8.0)  # 1.0 - 10.0
    infrastructure_score = Column(Float, default=7.0)  # Power, water, road access
    
    # Regional Cluster Validation (20-30km radius)
    regional_cluster_density_25km = Column(Float, default=5.0)  # Number of operating units in cluster
    regional_cluster_failure_rate_pct = Column(Float, default=15.0)  # % of units that failed in 25km radius
    
    # Epistemic Honesty / Data Confidence Level
    data_confidence_level = Column(String(30), default="moderate_proxy")  # high_verified, moderate_proxy, estimated
    
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    district = relationship("District", back_populates="market_data")
    sub_district = relationship("SubDistrict", back_populates="market_data")


class BusinessCategoryBenchmark(Base):
    __tablename__ = "business_market_benchmarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_code = Column(String(50), unique=True, index=True, nullable=False)  # kirana, dairy, food_processing, etc.
    category_name = Column(String(100), nullable=False)
    
    # Configurable population benchmarks
    minimum_population_per_business = Column(Float, default=600.0)
    ideal_population_per_business = Column(Float, default=1000.0)
    
    # OSM Overpass search tags & keywords
    osm_tags = Column(JSON, default=lambda: ["convenience", "supermarket", "general", "grocery", "shop"])
    
    # Scoring weights
    competition_weight = Column(Float, default=0.35)
    demand_weight = Column(Float, default=0.35)
    reach_weight = Column(Float, default=0.20)
    market_reach_weight = Column(Float, default=0.10)
    default_radius_km = Column(Float, default=5.0)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow)


class PopulationCache(Base):
    __tablename__ = "population_cache"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    location_key = Column(String(150), unique=True, index=True, nullable=False)  # village_a:nalgonda:telangana
    village_name = Column(String(100), index=True, nullable=False)
    block_name = Column(String(100), nullable=True)
    district_name = Column(String(100), index=True, nullable=False)
    state_name = Column(String(100), default="Telangana")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    village_population = Column(Integer, nullable=False)
    reachable_population_5km = Column(Integer, nullable=False)
    reachable_population_10km = Column(Integer, nullable=False)
    
    population_source = Column(String(100), default="Census 2011 / Open Data Portal")
    is_estimated = Column(Boolean, default=False)
    retrieved_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=True)


class CompetitorCache(Base):
    __tablename__ = "competitor_cache"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cache_key = Column(String(150), unique=True, index=True, nullable=False)  # kirana:17.05:79.27:5.0
    business_category = Column(String(50), index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_km = Column(Float, default=5.0)
    
    competitor_count = Column(Integer, default=0)
    competitor_names = Column(JSON, default=list)
    source = Column(String(100), default="OpenStreetMap Overpass API")
    retrieved_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=True)


class MarketAnalysisRecord(Base):
    __tablename__ = "market_analysis_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True, index=True)
    village_name = Column(String(100), nullable=False)
    district_name = Column(String(100), nullable=False)
    business_category = Column(String(50), nullable=False)
    radius_km = Column(Float, default=5.0)
    
    market_opportunity_score = Column(Float, nullable=False)
    market_potential = Column(String(50), nullable=False)  # HIGH_OPPORTUNITY, MODERATE_OPPORTUNITY, etc.
    market_saturation_percentage = Column(Float, nullable=False)
    recommendation_level = Column(String(50), nullable=False)  # PROCEED, REVIEW, HIGH_RISK
    full_analysis_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utcnow)


