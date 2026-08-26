from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserUpdate, UserRead, Token

router = APIRouter(prefix="/users", tags=["Users & Authentication"])


async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency that extracts user from Authorization Bearer token or returns mock default user."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                res = await db.execute(select(User).where(User.id == user_id))
                user = res.scalars().first()
                if user:
                    return user
        except JWTError:
            pass

    # Fallback to first active user in database (for smooth development / demo)
    res = await db.execute(select(User))
    user = res.scalars().first()
    if not user:
        # Create a default demo user if DB is completely empty
        user = User(
            phone_number="9876543210",
            full_name="Ramesh Kumar (Demo)",
            hashed_password=hash_password("password123"),
            available_margin_money=50000.0,
            annual_income=180000.0,
            state="Telangana",
            district="Nalgonda",
            sub_district="Miryalaguda",
            village="Alwal"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new rural entrepreneur."""
    res = await db.execute(select(User).where(User.phone_number == user_in.phone_number))
    if res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )

    user = User(
        phone_number=user_in.phone_number,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        preferred_language=user_in.preferred_language,
        social_category=user_in.social_category,
        is_differently_abled=user_in.is_differently_abled,
        available_margin_money=user_in.available_margin_money,
        annual_income=user_in.annual_income,
        education_level=user_in.education_level,
        state=user_in.state,
        district=user_in.district,
        sub_district=user_in.sub_district,
        village=user_in.village
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, user=UserRead.model_validate(user))


@router.post("/login", response_model=Token)
async def login_user(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Authenticate via phone number & password."""
    res = await db.execute(select(User).where(User.phone_number == credentials.phone_number))
    user = res.scalars().first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password"
        )

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current authenticated user profile."""
    return current_user


@router.put("/profile", response_model=UserRead)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update user demographics, margin money, or preferred language."""
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return current_user

