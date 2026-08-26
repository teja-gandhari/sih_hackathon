import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class District(Base):
    __tablename__ = "districts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    state_name = Column(String(100), nullable=False)
    district_name = Column(String(100), unique=True, index=True, nullable=False)
    state_code = Column(String(10), default="IN-TG")

    # Relationships
    sub_districts = relationship("SubDistrict", back_populates="district", cascade="all, delete-orphan")
    market_data = relationship("MarketData", back_populates="district", cascade="all, delete-orphan")


class SubDistrict(Base):
    __tablename__ = "sub_districts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    district_id = Column(String(36), ForeignKey("districts.id"), nullable=False, index=True)
    sub_district_name = Column(String(100), nullable=False, index=True)  # Block / Mandal / Taluk

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    district = relationship("District", back_populates="market_data")
    sub_district = relationship("SubDistrict", back_populates="market_data")

