from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.business import BusinessSector, BusinessType
from app.models.application import BusinessApplication
from app.schemas.business import (
    BusinessSectorRead,
    BusinessTypeRead,
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate
)
from app.routers.users import get_current_user

router = APIRouter(prefix="/businesses", tags=["Business Sectors & Applications"])


@router.get("/sectors", response_model=List[BusinessSectorRead])
async def list_sectors(db: AsyncSession = Depends(get_db)) -> Any:
    """List all 7 rural business sectors (Dairy, Food Processing, Retail, Agriculture, etc.)."""
    res = await db.execute(select(BusinessSector))
    sectors = res.scalars().all()
    return sectors


@router.get("/types", response_model=List[BusinessTypeRead])
async def list_business_types(
    sector_code: str = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List pre-configured business benchmark templates."""
    query = select(BusinessType)
    if sector_code:
        query = query.join(BusinessSector).where(BusinessSector.code == sector_code)
    
    res = await db.execute(query)
    types = res.scalars().all()
    return types


@router.post("/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    app_in: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new business feasibility application."""
    # Verify business type exists
    res = await db.execute(select(BusinessType).where(BusinessType.id == app_in.business_type_id))
    bt = res.scalars().first()
    if not bt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business type template not found"
        )

    application = BusinessApplication(
        user_id=current_user.id,
        business_type_id=app_in.business_type_id,
        district_id=app_in.district_id,
        sub_district_id=app_in.sub_district_id,
        village_id=app_in.village_id,
        scale_units=app_in.scale_units,
        target_price_per_unit=app_in.target_price_per_unit or bt.typical_ticket_size,
        user_margin_available=app_in.user_margin_available or current_user.available_margin_money,
        own_land_available=app_in.own_land_available,
        land_area_sqft=app_in.land_area_sqft,
        prior_experience_years=app_in.prior_experience_years,
        status="draft"
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    # Load relationship
    res_app = await db.execute(
        select(BusinessApplication)
        .options(selectinload(BusinessApplication.business_type))
        .where(BusinessApplication.id == application.id)
    )
    return res_app.scalars().first()


@router.get("/applications", response_model=List[ApplicationRead])
async def list_user_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List all business applications for current user."""
    res = await db.execute(
        select(BusinessApplication)
        .options(selectinload(BusinessApplication.business_type))
        .where(BusinessApplication.user_id == current_user.id)
    )
    return res.scalars().all()


@router.get("/applications/{app_id}", response_model=ApplicationRead)
async def get_application(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Retrieve specific application by ID."""
    res = await db.execute(
        select(BusinessApplication)
        .options(selectinload(BusinessApplication.business_type))
        .where(BusinessApplication.id == app_id, BusinessApplication.user_id == current_user.id)
    )
    application = res.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business application not found"
        )
    return application

