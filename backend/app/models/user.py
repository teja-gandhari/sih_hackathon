import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class LanguageEnum(str, enum.Enum):
    EN = "en"
    TE = "te"
    HI = "hi"


class SocialCategoryEnum(str, enum.Enum):
    GENERAL = "general"
    OBC = "obc"
    SC = "sc"
    ST = "st"
    MINORITY = "minority"
    WOMEN_ENTREPRENEUR = "women_entrepreneur"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String(15), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    
    preferred_language = Column(SQLEnum(LanguageEnum), default=LanguageEnum.TE, nullable=False)
    social_category = Column(SQLEnum(SocialCategoryEnum), default=SocialCategoryEnum.GENERAL, nullable=False)
    is_differently_abled = Column(Boolean, default=False)
    
    # Financial profile
    available_margin_money = Column(Float, default=0.0)
    annual_income = Column(Float, default=0.0)
    education_level = Column(String(50), default="10th_pass")
    
    # Location reference
    state = Column(String(100), default="Telangana")
    district = Column(String(100), default="Nalgonda")
    sub_district = Column(String(100), default="Miryalaguda")
    village = Column(String(100), default="Alwal")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications = relationship("BusinessApplication", back_populates="user", cascade="all, delete-orphan")

