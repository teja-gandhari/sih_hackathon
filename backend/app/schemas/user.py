from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from app.models.user import LanguageEnum, SocialCategoryEnum


class UserBase(BaseModel):
    phone_number: str
    email: Optional[EmailStr] = None
    full_name: str
    preferred_language: LanguageEnum = LanguageEnum.TE
    social_category: SocialCategoryEnum = SocialCategoryEnum.GENERAL
    is_differently_abled: bool = False
    available_margin_money: float = 0.0
    annual_income: float = 0.0
    education_level: str = "10th_pass"
    state: str = "Telangana"
    district: str = "Nalgonda"
    sub_district: str = "Miryalaguda"
    village: str = "Alwal"


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    phone_number: str
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    preferred_language: Optional[LanguageEnum] = None
    social_category: Optional[SocialCategoryEnum] = None
    is_differently_abled: Optional[bool] = None
    available_margin_money: Optional[float] = None
    annual_income: Optional[float] = None
    education_level: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    sub_district: Optional[str] = None
    village: Optional[str] = None


class UserRead(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

