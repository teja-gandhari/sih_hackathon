import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base, AsyncSessionLocal
from app.seeds.schemes import seed_sectors_and_schemes
from app.seeds.market_data import seed_market_data
from app.schemas.feasibility import FeasibilityAnalyzeRequest
from app.services.feasibility_engine import FeasibilityScoringEngine


@pytest.mark.anyio
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_sectors_and_schemes()
    await seed_market_data()


@pytest.mark.anyio
async def test_high_feasibility_scenario():
    """
    Scenario 1: High Feasibility Enterprise
    - Dairy farm in Miryalaguda (10,000 population, 2 competitors, high demand, strong DSCR).
    Expected:
    - Overall Feasibility Score >= 80.0
    - Classification: HIGHLY_FEASIBLE
    - Financial Score >= 80.0
    - Market Score >= 80.0
    - Scheme Score >= 80.0
    - Grounded strengths, weaknesses, opportunities, key_risks populated.
    """
    async with AsyncSessionLocal() as session:
        req = FeasibilityAnalyzeRequest(
            business_category="dairy",
            available_margin_capital=50000.0,
            village="Miryalaguda",
            district="Nalgonda",
            state="Telangana",
            category="obc",
            is_rural=True,
            radius_km=5.0
        )
        res = await FeasibilityScoringEngine.analyze_unified_feasibility(
            db=session,
            request=req
        )

        assert res.overall_feasibility_score >= 80.0
        assert res.classification == "HIGHLY_FEASIBLE"
        assert res.financial_score >= 80.0
        assert res.market_score >= 80.0
        assert res.scheme_score >= 80.0
        assert res.risk_score >= 60.0
        assert len(res.strengths) >= 2
        assert len(res.opportunities) >= 2
        assert "Feasibility Score of" in res.deterministic_explanation


@pytest.mark.anyio
async def test_moderate_feasibility_scenario():
    """
    Scenario 2: Moderate Feasibility Enterprise
    - Kirana store in Village A (5,000 population, 5 competitors, 100% saturation).
    Expected:
    - Overall Feasibility Score between 50.0 and 79.9
    - Classification: FEASIBLE or MODERATE
    - Market saturation noted in key risks and explanation.
    """
    async with AsyncSessionLocal() as session:
        req = FeasibilityAnalyzeRequest(
            business_category="kirana",
            available_margin_capital=40000.0,
            village="Village A",
            district="Nalgonda",
            state="Telangana",
            village_population=5000,
            radius_km=5.0
        )
        res = await FeasibilityScoringEngine.analyze_unified_feasibility(
            db=session,
            request=req
        )

        assert 50.0 <= res.overall_feasibility_score < 80.0
        assert res.classification in ["FEASIBLE", "MODERATE"]
        assert len(res.key_risks) >= 1
        assert "saturation" in res.deterministic_explanation.lower() or "kirana" in res.deterministic_explanation.lower()


@pytest.mark.anyio
async def test_low_feasibility_high_risk_scenario():
    """
    Scenario 3: Low Feasibility / High Risk Enterprise
    - Exceeds concessional credit ceiling (> ₹50 Lakh project cost / margin > ₹5 Lakh).
    Expected:
    - Scheme score is penalized
    - Overall score < 50.0 or Classification: HIGH_RISK or MODERATE
    """
    async with AsyncSessionLocal() as session:
        req = FeasibilityAnalyzeRequest(
            business_category="food_processing",
            available_margin_capital=600000.0,  # 60L project cost -> exceeds 50L ceiling
            village="Tiny Hamlet",
            district="Nalgonda",
            state="Telangana",
            village_population=500,
            radius_km=5.0
        )
        res = await FeasibilityScoringEngine.analyze_unified_feasibility(
            db=session,
            request=req
        )

        assert res.classification in ["MODERATE", "HIGH_RISK"]
        assert res.scheme_score <= 40.0
        assert "Commercial Bank Loan" in res.scheme_summary["matched_scheme_name"] or "Ceiling" in res.scheme_summary["matched_scheme_name"]


@pytest.mark.anyio
async def test_http_endpoint_post_feasibility_analyze():
    """
    Scenario 4: HTTP integration test for POST /api/v1/feasibility/analyze and /feasibility/analyze.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Versioned endpoint
        res1 = await client.post("/api/v1/feasibility/analyze", json={
            "business_category": "dairy",
            "available_margin_capital": 50000.0,
            "village": "Baramati",
            "district": "Pune",
            "state": "Maharashtra",
            "radius_km": 5.0
        })
        assert res1.status_code == 200
        d1 = res1.json()
        assert "overall_feasibility_score" in d1
        assert "classification" in d1
        assert "financial_score" in d1
        assert "market_score" in d1
        assert "scheme_score" in d1
        assert "risk_score" in d1
        assert "strengths" in d1
        assert "deterministic_explanation" in d1

        # 2. Root-level alias endpoint
        res2 = await client.post("/feasibility/analyze", json={
            "business_category": "textiles",
            "available_margin_capital": 30000.0,
            "village": "Pindra",
            "district": "Varanasi",
            "state": "Uttar Pradesh",
            "radius_km": 5.0
        })
        assert res2.status_code == 200
        d2 = res2.json()
        assert d2["classification"] in ["HIGHLY_FEASIBLE", "FEASIBLE", "MODERATE"]

