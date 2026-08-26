import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, JSON, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class BusinessSector(Base):
    __tablename__ = "business_sectors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, index=True, nullable=False)  # dairy, retail, agriculture, etc.
    name_en = Column(String(100), nullable=False)
    name_te = Column(String(100), nullable=False)
    name_hi = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    icon_name = Column(String(50), default="business")

    # Relationships
    business_types = relationship("BusinessType", back_populates="sector", cascade="all, delete-orphan")


class BusinessType(Base):
    __tablename__ = "business_types"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sector_id = Column(String(36), ForeignKey("business_sectors.id"), nullable=False, index=True)
    code = Column(String(100), unique=True, index=True, nullable=False)
    
    # Multilingual Names & Descriptions
    name_en = Column(String(150), nullable=False)
    name_te = Column(String(150), nullable=False)
    name_hi = Column(String(150), nullable=False)
    description_en = Column(String(1000), nullable=True)
    description_te = Column(String(1000), nullable=True)
    description_hi = Column(String(1000), nullable=True)
    
    # Scale & Economics benchmarks
    unit_label = Column(String(50), default="units")  # e.g., "Animals", "Sqft", "Tons/Month"
    default_scale = Column(Integer, default=5)
    default_capex = Column(Float, default=300000.0)
    default_monthly_opex = Column(Float, default=20000.0)
    default_monthly_revenue = Column(Float, default=35000.0)
    
    # Purchasing Power & Cultural Fit Proxies
    typical_ticket_size = Column(Float, default=50.0)
    min_purchasing_power_tier = Column(String(30), default="low")
    requires_daily_footfall = Column(Boolean, default=False)
    is_export_or_wholesale = Column(Boolean, default=False)
    seasonal_cyclical = Column(Boolean, default=False)
    
    # Detailed Benchmark Breakdown
    capex_breakdown = Column(JSON, default=dict)
    opex_breakdown = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sector = relationship("BusinessSector", back_populates="business_types")
    applications = relationship("BusinessApplication", back_populates="business_type")

