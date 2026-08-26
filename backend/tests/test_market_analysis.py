import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base
from app.seeds.schemes import seed_sectors_and_schemes
from app.seeds.market_data import seed_market_data
from app.schemas.market import MarketAnalysisRequest
from app.services.market_analysis_engine import HyperLocalMarketAnalysisEngine
from app.core.database import AsyncSessionLocal


@pytest.mark.anyio
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_sectors_and_schemes()
    await seed_market_data()


@pytest.mark.anyio
async def test_case_1_kirana_5000_pop_5_competitors():
    """
    Test Case 1: Kirana in village with 5,000 population and 5 existing competitors.
    Benchmark: 1,000 people per Kirana shop.
    Expected:
    - Existing population per competitor = 1,000
    - Projected population per business = 833.3
    - Estimated market capacity = 5
    - Capacity gap = 0
    - Saturation = 100% (High saturation)
    - Competition level = HIGH
    - Recommendation = should_proceed is False
    """
    async with AsyncSessionLocal() as session:
        req = MarketAnalysisRequest(
            village="Village A",
            district="Nalgonda",
            business_category="kirana",
            village_population=5000,
            radius_km=5.0
        )
        from unittest.mock import patch
        with patch("app.services.osm_service.OpenStreetMapService.get_competitors", return_value=(5, ["K1", "K2", "K3", "K4", "K5"], "Test Mock")):
            res = await HyperLocalMarketAnalysisEngine.analyze_market_viability(
                db=session,
                request=req
            )

            assert res.population_analysis.reachable_population == 5000
            assert res.competition_analysis.existing_competitor_count == 5
            assert res.competition_analysis.population_per_existing_competitor == 1000.0
            assert round(res.competition_analysis.projected_population_per_business, 1) == 833.3
            assert res.market_capacity_analysis.estimated_market_capacity == 5
            assert res.market_capacity_analysis.capacity_gap == 0
            assert res.market_capacity_analysis.market_saturation_percentage == 100.0
            assert res.competition_analysis.competition_level == "HIGH"
            assert res.recommendation.should_proceed is False
            assert res.recommendation.recommendation_level in ["REVIEW", "HIGH_RISK"]
            assert "approaching saturation" in res.recommendation.summary.lower()



@pytest.mark.anyio
async def test_case_2_kirana_10000_pop_3_competitors():
    """
    Test Case 2: Kirana in village with 10,000 population and 3 existing competitors.
    Benchmark: 1,000 people per Kirana shop.
    Expected:
    - Existing population per competitor = 3,333.3
    - Projected population per business = 2,500.0
    - Estimated market capacity = 10
    - Capacity gap = 7
    - Saturation = 30.0%
    - Competition level = LOW or MODERATE
    - Opportunity classification = HIGH_OPPORTUNITY
    - Recommendation = should_proceed is True, level is PROCEED
    """
    async with AsyncSessionLocal() as session:
        req = MarketAnalysisRequest(
            village="Miryalaguda",
            district="Nalgonda",
            business_category="kirana",
            village_population=10000,
            radius_km=5.0
        )
        # Note: Miryalaguda demo in OSM service returns default or we override pop to 10k with 3 competitors
        # Let's mock or check calculation
        from unittest.mock import patch
        with patch("app.services.osm_service.OpenStreetMapService.get_competitors", return_value=(3, ["Shop 1", "Shop 2", "Shop 3"], "Test Mock")):
            res = await HyperLocalMarketAnalysisEngine.analyze_market_viability(
                db=session,
                request=req
            )

            assert res.population_analysis.reachable_population == 10000
            assert res.competition_analysis.existing_competitor_count == 3
            assert round(res.competition_analysis.projected_population_per_business, 1) == 2500.0
            assert res.market_capacity_analysis.estimated_market_capacity == 10
            assert res.market_capacity_analysis.capacity_gap == 7
            assert res.market_capacity_analysis.market_saturation_percentage == 30.0
            assert res.market_opportunity.score >= 80.0
            assert res.market_opportunity.classification == "HIGH_OPPORTUNITY"
            assert res.recommendation.should_proceed is True
            assert res.recommendation.recommendation_level == "PROCEED"


@pytest.mark.anyio
async def test_case_3_zero_competitors_safe_division():
    """
    Test Case 3: Zero existing competitors (unserved market).
    Expected:
    - No ZeroDivisionError
    - Unmet demand opportunity signal
    - High opportunity score
    - should_proceed is True
    """
    async with AsyncSessionLocal() as session:
        req = MarketAnalysisRequest(
            village="New Settlement",
            district="Nalgonda",
            business_category="handicrafts",
            village_population=4000,
            radius_km=5.0
        )
        from unittest.mock import patch
        with patch("app.services.osm_service.OpenStreetMapService.get_competitors", return_value=(0, [], "Test Mock")):
            res = await HyperLocalMarketAnalysisEngine.analyze_market_viability(
                db=session,
                request=req
            )

            assert res.competition_analysis.existing_competitor_count == 0
            assert res.competition_analysis.population_per_existing_competitor == 4000.0
            assert res.competition_analysis.projected_population_per_business == 4000.0
            assert res.market_opportunity.competition_gap_score >= 95.0
            assert res.recommendation.should_proceed is True
            assert "0 registered competitors" in res.recommendation.summary


@pytest.mark.anyio
async def test_case_4_small_population_many_competitors():
    """
    Test Case 4: Tiny population (500) with 5 existing shops.
    Expected:
    - High saturation
    - High risk
    - Projected population per business = 83.3 (< minimum 600)
    - Recommendation level = HIGH_RISK
    """
    async with AsyncSessionLocal() as session:
        req = MarketAnalysisRequest(
            village="Tiny Hamlet",
            district="Nalgonda",
            business_category="kirana",
            village_population=500,
            radius_km=5.0
        )
        from unittest.mock import patch
        with patch("app.services.osm_service.OpenStreetMapService.get_competitors", return_value=(5, ["S1", "S2", "S3", "S4", "S5"], "Test Mock")):
            res = await HyperLocalMarketAnalysisEngine.analyze_market_viability(
                db=session,
                request=req
            )

            assert res.competition_analysis.existing_competitor_count == 5
            assert round(res.competition_analysis.projected_population_per_business, 1) == 83.3
            assert res.competition_analysis.competition_level == "HIGH"
            assert res.recommendation.should_proceed is False
            assert res.recommendation.recommendation_level == "HIGH_RISK"


@pytest.mark.anyio
async def test_case_5_missing_population_graceful_fallback():
    """
    Test Case 5: Missing / Unknown village population.
    Expected:
    - Falls back gracefully to Gram Panchayat regional benchmark (5,000)
    - is_estimated is True
    - Does not crash
    """
    async with AsyncSessionLocal() as session:
        req = MarketAnalysisRequest(
            village="Unknown Remote Village XYZ",
            district="Nalgonda",
            business_category="dairy"
        )
        res = await HyperLocalMarketAnalysisEngine.analyze_market_viability(
            db=session,
            request=req
        )

        assert res.population_analysis.is_estimated is True
        assert res.population_analysis.reachable_population >= 5000
        assert "Estimated" in res.population_analysis.population_source
        assert res.data_quality.confidence in ["MEDIUM", "HIGH"]


@pytest.mark.anyio
async def test_case_6_http_endpoint_post_market_analyze():
    """
    Test Case 6: HTTP Integration test for POST /api/v1/market/analyze & /market/analyze.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Versioned endpoint
        r1 = await client.post("/api/v1/market/analyze", json={
            "village": "Village A",
            "district": "Nalgonda",
            "business_category": "kirana",
            "radius_km": 5.0
        })
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["business_category"] == "kirana"
        assert d1["population_analysis"]["reachable_population"] == 5000
        assert "market_opportunity" in d1
        assert "recommendation" in d1

        # 2. Root-level alias endpoint
        r2 = await client.post("/market/analyze", json={
            "village": "Miryalaguda",
            "district": "Nalgonda",
            "business_category": "dairy",
            "radius_km": 5.0
        })
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["business_category"] == "dairy"
        assert d2["market_capacity_analysis"]["recommended_population_per_business"] == 800.0
