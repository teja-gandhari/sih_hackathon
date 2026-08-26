import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, JSON, DateTime, Integer
from app.core.database import Base


class GovernmentScheme(Base):
    __tablename__ = "government_schemes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_code = Column(String(50), unique=True, index=True, nullable=False)
    
    # Multilingual Titles
    name_en = Column(String(200), nullable=False)
    name_te = Column(String(200), nullable=False)
    name_hi = Column(String(200), nullable=False)
    nodal_agency = Column(String(100), default="Ministry of MSME / KVIC")
    
    # Cost constraints
    min_project_cost = Column(Float, default=10000.0)
    max_project_cost = Column(Float, default=5000000.0)
    
    # Margin requirements
    general_margin_pct = Column(Float, default=10.0)
    special_margin_pct = Column(Float, default=5.0)  # SC/ST/Women/Minorities
    
    # Subsidies
    general_subsidy_rural_pct = Column(Float, default=25.0)
    general_subsidy_urban_pct = Column(Float, default=15.0)
    special_subsidy_rural_pct = Column(Float, default=35.0)
    special_subsidy_urban_pct = Column(Float, default=25.0)
    max_subsidy_amount = Column(Float, default=1250000.0)
    
    # Interest & Tenure
    default_annual_interest_rate = Column(Float, default=8.5)
    interest_subvention_pct = Column(Float, default=2.0)
    max_tenure_months = Column(Integer, default=60)
    
    # Eligibility arrays
    eligible_sectors = Column(JSON, default=list)  # ["dairy", "agriculture", "food_processing", "retail", "textiles", "handicrafts", "services"]
    eligible_categories = Column(JSON, default=list)  # ["general", "obc", "sc", "st", "minority", "women_entrepreneur"]
    min_applicant_age = Column(Integer, default=18)
    min_education_required = Column(String(50), default="8th_pass")
    
    description_en = Column(String(1000), nullable=True)
    description_te = Column(String(1000), nullable=True)
    description_hi = Column(String(1000), nullable=True)
    application_portal_url = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

