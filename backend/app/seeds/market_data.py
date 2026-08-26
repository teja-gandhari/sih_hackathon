import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.market import District, SubDistrict, Village, MarketData


DISTRICTS_DATA = [
    {
        "state_name": "Telangana",
        "district_name": "Nalgonda",
        "state_code": "IN-TG",
        "sub_districts": [
            {
                "name": "Miryalaguda",
                "villages": ["Alwal", "Tadipatri", "Gudur"],
                "pincode": "508207"
            },
            {
                "name": "Devarakonda",
                "villages": ["Kondrapole", "Padamati Palle"],
                "pincode": "508248"
            }
        ],
        "market_benchmarks": [
            {
                "sector_code": "dairy",
                "demand_index": 8.8,
                "formal_competitor_count": 2,
                "estimated_informal_competitor_count": 5,
                "mgnrega_daily_wage_rate": 300.0,
                "average_monthly_household_income": 15500.0,
                "purchasing_power_tier": "lower_middle",
                "seasonal_dependence": "heavy_agri_cyclical",
                "harvest_months": ["Oct", "Nov", "Dec", "Apr", "May"],
                "nearest_mandi_distance_km": 4.5,
                "raw_material_availability_score": 8.8,
                "infrastructure_score": 7.5,
                "regional_cluster_density_25km": 8.0,
                "regional_cluster_failure_rate_pct": 11.5,
                "data_confidence_level": "high_verified"
            },
            {
                "sector_code": "food_processing",
                "demand_index": 8.2,
                "formal_competitor_count": 1,
                "estimated_informal_competitor_count": 3,
                "mgnrega_daily_wage_rate": 300.0,
                "average_monthly_household_income": 15500.0,
                "purchasing_power_tier": "lower_middle",
                "seasonal_dependence": "heavy_agri_cyclical",
                "harvest_months": ["Oct", "Nov", "Dec", "Apr", "May"],
                "nearest_mandi_distance_km": 5.0,
                "raw_material_availability_score": 9.2,
                "infrastructure_score": 7.5,
                "regional_cluster_density_25km": 5.0,
                "regional_cluster_failure_rate_pct": 9.0,
                "data_confidence_level": "high_verified"
            }
        ]
    },
    {
        "state_name": "Telangana",
        "district_name": "Warangal",
        "state_code": "IN-TG",
        "sub_districts": [
            {
                "name": "Narsampet",
                "villages": ["Chennaraopet", "Khanapur"],
                "pincode": "506132"
            }
        ],
        "market_benchmarks": [
            {
                "sector_code": "retail",
                "demand_index": 7.6,
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
                "regional_cluster_failure_rate_pct": 16.0,
                "data_confidence_level": "moderate_proxy"
            }
        ]
    }
]


async def seed_market_data():
    """Seed districts, sub-districts, villages, and local economic proxy metrics."""
    async with AsyncSessionLocal() as session:
        for dist in DISTRICTS_DATA:
            res_d = await session.execute(select(District).where(District.district_name == dist["district_name"]))
            dist_obj = res_d.scalars().first()
            if not dist_obj:
                dist_obj = District(
                    state_name=dist["state_name"],
                    district_name=dist["district_name"],
                    state_code=dist["state_code"]
                )
                session.add(dist_obj)
                await session.flush()

            for sd in dist.get("sub_districts", []):
                res_sd = await session.execute(select(SubDistrict).where(
                    SubDistrict.district_id == dist_obj.id,
                    SubDistrict.sub_district_name == sd["name"]
                ))
                sd_obj = res_sd.scalars().first()
                if not sd_obj:
                    sd_obj = SubDistrict(
                        district_id=dist_obj.id,
                        sub_district_name=sd["name"]
                    )
                    session.add(sd_obj)
                    await session.flush()

                for v_name in sd.get("villages", []):
                    res_v = await session.execute(select(Village).where(
                        Village.sub_district_id == sd_obj.id,
                        Village.village_name == v_name
                    ))
                    if not res_v.scalars().first():
                        v_obj = Village(
                            sub_district_id=sd_obj.id,
                            village_name=v_name,
                            pincode=sd.get("pincode")
                        )
                        session.add(v_obj)

            for mb in dist.get("market_benchmarks", []):
                res_mb = await session.execute(select(MarketData).where(
                    MarketData.district_id == dist_obj.id,
                    MarketData.sector_code == mb["sector_code"]
                ))
                if not res_mb.scalars().first():
                    mb_obj = MarketData(
                        district_id=dist_obj.id,
                        sector_code=mb["sector_code"],
                        demand_index=mb["demand_index"],
                        formal_competitor_count=mb["formal_competitor_count"],
                        estimated_informal_competitor_count=mb["estimated_informal_competitor_count"],
                        mgnrega_daily_wage_rate=mb["mgnrega_daily_wage_rate"],
                        average_monthly_household_income=mb["average_monthly_household_income"],
                        purchasing_power_tier=mb["purchasing_power_tier"],
                        seasonal_dependence=mb["seasonal_dependence"],
                        harvest_months=mb["harvest_months"],
                        nearest_mandi_distance_km=mb["nearest_mandi_distance_km"],
                        raw_material_availability_score=mb["raw_material_availability_score"],
                        infrastructure_score=mb["infrastructure_score"],
                        regional_cluster_density_25km=mb["regional_cluster_density_25km"],
                        regional_cluster_failure_rate_pct=mb["regional_cluster_failure_rate_pct"],
                        data_confidence_level=mb["data_confidence_level"]
                    )
                    session.add(mb_obj)

        await session.commit()
        print("Successfully seeded location hierarchy and hyper-local market benchmarks.")


if __name__ == "__main__":
    asyncio.run(seed_market_data())

