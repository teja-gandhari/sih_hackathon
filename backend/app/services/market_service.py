from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.market import District, SubDistrict, Village, MarketData
from app.schemas.market import MarketDataRead


class MarketService:
    """
    Hyper-Local Market Service.
    Provides local demand indices, competitor analysis (formal + informal),
    MGNREGA wage benchmarks, purchasing power tiers, and regional cluster indicators.
    """

    DEFAULT_BENCHMARKS = {
        "dairy": {
            "demand_index": 8.5,
            "formal_competitor_count": 2,
            "estimated_informal_competitor_count": 5,
            "mgnrega_daily_wage_rate": 300.0,
            "average_monthly_household_income": 15000.0,
            "purchasing_power_tier": "lower_middle",
            "seasonal_dependence": "heavy_agri_cyclical",
            "harvest_months": ["Oct", "Nov", "Dec", "Apr", "May"],
            "nearest_mandi_distance_km": 4.5,
            "raw_material_availability_score": 8.5,
            "infrastructure_score": 7.5,
            "regional_cluster_density_25km": 8.0,
            "regional_cluster_failure_rate_pct": 12.0,
            "data_confidence_level": "moderate_proxy"
        },
        "food_processing": {
            "demand_index": 8.0,
            "formal_competitor_count": 1,
            "estimated_informal_competitor_count": 3,
            "mgnrega_daily_wage_rate": 300.0,
            "average_monthly_household_income": 15000.0,
            "purchasing_power_tier": "lower_middle",
            "seasonal_dependence": "heavy_agri_cyclical",
            "harvest_months": ["Oct", "Nov", "Dec", "Apr", "May"],
            "nearest_mandi_distance_km": 6.0,
            "raw_material_availability_score": 9.0,
            "infrastructure_score": 7.0,
            "regional_cluster_density_25km": 4.0,
            "regional_cluster_failure_rate_pct": 10.0,
            "data_confidence_level": "moderate_proxy"
        },
        "retail": {
            "demand_index": 7.5,
            "formal_competitor_count": 3,
            "estimated_informal_competitor_count": 6,
            "mgnrega_daily_wage_rate": 300.0,
            "average_monthly_household_income": 14000.0,
            "purchasing_power_tier": "low",
            "seasonal_dependence": "moderate",
            "harvest_months": ["Oct", "Nov", "Dec", "Apr", "May"],
            "nearest_mandi_distance_km": 8.0,
            "raw_material_availability_score": 7.0,
            "infrastructure_score": 7.0,
            "regional_cluster_density_25km": 6.0,
            "regional_cluster_failure_rate_pct": 18.0,
            "data_confidence_level": "proxy_estimated"
        },
        "agriculture": {
            "demand_index": 8.2,
            "formal_competitor_count": 1,
            "estimated_informal_competitor_count": 4,
            "mgnrega_daily_wage_rate": 300.0,
            "average_monthly_household_income": 14500.0,
            "purchasing_power_tier": "lower_middle",
            "seasonal_dependence": "heavy_agri_cyclical",
            "harvest_months": ["Oct", "Nov", "Dec", "Apr", "May"],
            "nearest_mandi_distance_km": 5.0,
            "raw_material_availability_score": 8.8,
            "infrastructure_score": 6.8,
            "regional_cluster_density_25km": 7.0,
            "regional_cluster_failure_rate_pct": 14.0,
            "data_confidence_level": "moderate_proxy"
        },
        "textiles": {
            "demand_index": 6.8,
            "formal_competitor_count": 1,
            "estimated_informal_competitor_count": 4,
            "mgnrega_daily_wage_rate": 300.0,
            "average_monthly_household_income": 14000.0,
            "purchasing_power_tier": "low",
            "seasonal_dependence": "heavy_agri_cyclical",
            "harvest_months": ["Oct", "Nov", "Dec", "Apr", "May"],
            "nearest_mandi_distance_km": 12.0,
            "raw_material_availability_score": 6.5,
            "infrastructure_score": 6.5,
            "regional_cluster_density_25km": 3.0,
            "regional_cluster_failure_rate_pct": 22.0,
            "data_confidence_level": "proxy_estimated"
        },
        "handicrafts": {
            "demand_index": 6.5,
            "formal_competitor_count": 0,
            "estimated_informal_competitor_count": 3,
            "mgnrega_daily_wage_rate": 300.0,
            "average_monthly_household_income": 13500.0,
            "purchasing_power_tier": "low",
            "seasonal_dependence": "heavy_agri_cyclical",
            "harvest_months": ["Oct", "Nov", "Dec", "Apr", "May"],
            "nearest_mandi_distance_km": 15.0,
            "raw_material_availability_score": 8.0,
            "infrastructure_score": 6.0,
            "regional_cluster_density_25km": 2.0,
            "regional_cluster_failure_rate_pct": 25.0,
            "data_confidence_level": "proxy_estimated"
        },
        "services": {
            "demand_index": 7.8,
            "formal_competitor_count": 2,
            "estimated_informal_competitor_count": 3,
            "mgnrega_daily_wage_rate": 300.0,
            "average_monthly_household_income": 15000.0,
            "purchasing_power_tier": "lower_middle",
            "seasonal_dependence": "moderate",
            "harvest_months": ["Oct", "Nov", "Dec", "Apr", "May"],
            "nearest_mandi_distance_km": 7.0,
            "raw_material_availability_score": 7.5,
            "infrastructure_score": 7.5,
            "regional_cluster_density_25km": 5.0,
            "regional_cluster_failure_rate_pct": 15.0,
            "data_confidence_level": "moderate_proxy"
        }
    }

    @classmethod
    async def get_market_indicators(
        cls,
        db: AsyncSession,
        sector_code: str,
        district_id: Optional[str] = None,
        sub_district_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves database market data or falls back to calibrated sector benchmarks.
        """
        sector_clean = sector_code.lower()
        
        # Try finding exact record in database if IDs provided
        if district_id:
            query = select(MarketData).where(
                MarketData.district_id == district_id,
                MarketData.sector_code == sector_clean
            )
            if sub_district_id:
                query = query.where(MarketData.sub_district_id == sub_district_id)
                
            result = await db.execute(query)
            db_record = result.scalars().first()
            if db_record:
                return {
                    "demand_index": db_record.demand_index,
                    "formal_competitor_count": db_record.formal_competitor_count,
                    "estimated_informal_competitor_count": db_record.estimated_informal_competitor_count,
                    "mgnrega_daily_wage_rate": db_record.mgnrega_daily_wage_rate,
                    "average_monthly_household_income": db_record.average_monthly_household_income,
                    "purchasing_power_tier": db_record.purchasing_power_tier,
                    "seasonal_dependence": db_record.seasonal_dependence,
                    "harvest_months": db_record.harvest_months,
                    "nearest_mandi_distance_km": db_record.nearest_mandi_distance_km,
                    "raw_material_availability_score": db_record.raw_material_availability_score,
                    "infrastructure_score": db_record.infrastructure_score,
                    "regional_cluster_density_25km": db_record.regional_cluster_density_25km,
                    "regional_cluster_failure_rate_pct": db_record.regional_cluster_failure_rate_pct,
                    "data_confidence_level": db_record.data_confidence_level,
                    "notes": db_record.notes
                }

        # Fallback to calibrated default benchmarks
        return cls.DEFAULT_BENCHMARKS.get(sector_clean, cls.DEFAULT_BENCHMARKS["dairy"])

