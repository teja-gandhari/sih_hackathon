import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class BusinessApplication(Base):
    __tablename__ = "business_applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    business_type_id = Column(String(36), ForeignKey("business_types.id"), nullable=False, index=True)
    
    # Location overrides (if different from user profile)
    district_id = Column(String(36), ForeignKey("districts.id"), nullable=True)
    sub_district_id = Column(String(36), ForeignKey("sub_districts.id"), nullable=True)
    village_id = Column(String(36), ForeignKey("villages.id"), nullable=True)
    
    # Application Parameters
    scale_units = Column(Integer, default=5)  # e.g., 5 animals, 1 machine, 400 sqft shop
    target_price_per_unit = Column(Float, nullable=True)  # user's planned price point
    user_margin_available = Column(Float, default=50000.0)  # user cash on hand
    own_land_available = Column(Boolean, default=True)
    land_area_sqft = Column(Float, default=1000.0)
    prior_experience_years = Column(Float, default=1.0)
    
    status = Column(String(30), default="draft")  # draft, calculated, evaluated, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="applications")
    business_type = relationship("BusinessType", back_populates="applications")
    financial_plan = relationship("FinancialPlan", back_populates="application", uselist=False, cascade="all, delete-orphan")
    feasibility_assessment = relationship("FeasibilityAssessment", back_populates="application", uselist=False, cascade="all, delete-orphan")


class FinancialPlan(Base):
    __tablename__ = "financial_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("business_applications.id"), unique=True, nullable=False, index=True)
    
    # Project Cost Architecture
    total_capex = Column(Float, default=0.0)
    total_opex_monthly = Column(Float, default=0.0)
    working_capital_buffer = Column(Float, default=0.0)  # 2-3 months OPEX + Lean season buffer
    total_project_cost = Column(Float, default=0.0)
    
    # Capital Structuring
    user_margin_amount = Column(Float, default=0.0)
    user_margin_pct = Column(Float, default=10.0)
    subsidy_amount_eligible = Column(Float, default=0.0)
    subsidy_pct = Column(Float, default=0.0)
    matched_scheme_code = Column(String(50), default="PMEGP")
    
    # Debt & Repayment
    net_bank_loan_required = Column(Float, default=0.0)
    loan_tenure_months = Column(Integer, default=60)
    annual_interest_rate = Column(Float, default=8.5)
    monthly_emi_amount = Column(Float, default=0.0)
    
    # Profitability & Bankability Ratios
    projected_monthly_revenue = Column(Float, default=0.0)
    monthly_gross_profit = Column(Float, default=0.0)
    monthly_net_profit = Column(Float, default=0.0)  # Revenue - OPEX - EMI - Depreciation
    break_even_months = Column(Float, default=0.0)
    dscr_ratio = Column(Float, default=0.0)  # Debt Service Coverage Ratio (Target >= 1.5)
    roi_percentage = Column(Float, default=0.0)
    payback_period_years = Column(Float, default=0.0)
    
    # Detailed Schedules
    cash_flow_5yr = Column(JSON, default=dict)
    cost_breakdown = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("BusinessApplication", back_populates="financial_plan")


class FeasibilityAssessment(Base):
    __tablename__ = "feasibility_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("business_applications.id"), unique=True, nullable=False, index=True)
    
    # Scores (0 - 100)
    overall_score = Column(Float, default=0.0)
    market_demand_score = Column(Float, default=0.0)
    financial_viability_score = Column(Float, default=0.0)
    purchasing_power_fit_score = Column(Float, default=0.0)
    resource_readiness_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)  # Lower is safer
    
    viability_rating = Column(String(50), default="moderate_feasibility")  # high_feasibility, moderate_feasibility, high_risk, not_recommended
    market_gap_classification = Column(String(50), default="viable_and_unserved")  # viable_and_unserved, niche_weekly_market, unviable_purchasing_power_gap, saturated_informal_market
    
    # Deep Rural Market Risk Warnings
    informal_competition_warning = Column(Text, nullable=True)
    seasonal_cashflow_warning = Column(Text, nullable=True)
    regional_cluster_signal = Column(Text, nullable=True)
    data_confidence_level = Column(String(30), default="moderate_proxy")
    
    # AI Synthesis Outputs
    matched_schemes = Column(JSON, default=list)
    swot_analysis = Column(JSON, default=dict)  # {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}
    localized_advisory_text = Column(JSON, default=dict)  # {"en": "...", "te": "...", "hi": "..."}
    voice_script_text = Column(JSON, default=dict)  # {"en": "...", "te": "...", "hi": "..."}
    key_recommendations = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("BusinessApplication", back_populates="feasibility_assessment")

