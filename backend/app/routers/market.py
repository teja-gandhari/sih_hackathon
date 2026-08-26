from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.market import District, SubDistrict, Village, MarketData
from app.schemas.market import DistrictRead, SubDistrictRead, VillageRead, MarketDataRead
from app.services.market_service import MarketService

router = APIRouter(prefix="/market", tags=["Location & Hyper-Local Market Data"])


@router.get("/districts")
async def list_districts(db: AsyncSession = Depends(get_db)) -> Any:
    """List all available districts and states."""
    res = await db.execute(select(District))
    districts = res.scalars().all()
    if not districts:
        return [
            {"id": "dist-tg-nalgonda", "state_name": "Telangana", "district_name": "Nalgonda",
             "state_code": "IN-TG", "name": "Nalgonda", "state": "Telangana", "population": 1850000},
            {"id": "dist-tg-warangal", "state_name": "Telangana", "district_name": "Warangal",
             "state_code": "IN-TG", "name": "Warangal", "state": "Telangana", "population": 1450000}
        ]
    return [
        {
            "id": str(d.id),
            "state_name": d.state_name,
            "district_name": d.district_name,
            "state_code": d.state_code,
            "name": d.district_name,
            "state": d.state_name,
            "population": getattr(d, "population", None)
        }
        for d in districts
    ]


@router.get("/sub-districts", response_model=List[SubDistrictRead])
async def list_sub_districts(
    district_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List blocks/mandals/taluks in a district."""
    query = select(SubDistrict)
    if district_id:
        query = query.where(SubDistrict.district_id == district_id)
    res = await db.execute(query)
    subs = res.scalars().all()
    return subs


@router.get("/villages", response_model=List[VillageRead])
async def list_villages(
    sub_district_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List villages in a sub-district/mandal."""
    query = select(Village)
    if sub_district_id:
        query = query.where(Village.sub_district_id == sub_district_id)
    res = await db.execute(query)
    villages = res.scalars().all()
    return villages


@router.get("/indicators")
async def get_market_indicators(
    sector_code: str = Query("dairy", description="Sector code e.g. dairy, food_processing, retail"),
    district_id: Optional[str] = None,
    sub_district_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get hyper-local market indicators: demand index, competitor counts (formal + informal),
    MGNREGA wage rate, purchasing power tier, seasonality, and regional cluster metrics.
    """
    return await MarketService.get_market_indicators(
        db=db,
        sector_code=sector_code,
        district_id=district_id,
        sub_district_id=sub_district_id
    )

