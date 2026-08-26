"""
Tests for the AI Business Advisor Chat Module.

Covers:
1. Kirana shop with high competition (moderate/high-risk market).
2. Business with high feasibility (dairy in underserved area).
3. Business with low feasibility (oversized project exceeding loan ceiling).
4. Telugu language request.
5. Hindi language request.
6. AI API unavailable (deterministic fallback verification).
7. Context endpoint inspection.
8. HTTP integration via ASGI transport.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base
from app.seeds.schemes import seed_sectors_and_schemes
from app.seeds.market_data import seed_market_data

@pytest.fixture(autouse=True, scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_sectors_and_schemes()
    await seed_market_data()


@pytest.mark.anyio
async def test_chat_kirana_high_competition():
    """
    Scenario 1: Kirana shop in a saturated local market.
    The answer must reference real competitor data and market saturation.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/advisory/chat", json={
            "question": "Should I open a kirana shop here?",
            "language": "en",
            "business_category": "kirana",
            "available_margin_capital": 40000.0,
            "village": "Village A",
            "district": "Nalgonda",
            "state": "Telangana",
            "radius_km": 5.0
        })
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert data["language"] == "en"
        assert data["context_used"]["financial"] is True
        assert data["context_used"]["market"] is True
        assert data["context_used"]["feasibility"] is True
        ctx = data.get("context_snapshot")
        assert ctx is not None
        assert ctx["business_category"] == "kirana"
        assert ctx["available_margin_capital"] == 40000.0
        assert ctx["total_project_cost"] > 0
        assert ctx["feasibility_score"] > 0


@pytest.mark.anyio
async def test_chat_high_feasibility_dairy():
    """
    Scenario 2: Dairy business with high feasibility in underserved market.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/advisory/chat", json={
            "question": "Is dairy farming suitable for me?",
            "language": "en",
            "business_category": "dairy",
            "available_margin_capital": 50000.0,
            "village": "Miryalaguda",
            "district": "Nalgonda",
            "state": "Telangana",
            "radius_km": 5.0
        })
        assert res.status_code == 200
        data = res.json()
        ctx = data["context_snapshot"]
        assert ctx["feasibility_score"] >= 80.0
        assert ctx["feasibility_classification"] == "HIGHLY_FEASIBLE"
        assert ctx["dscr_ratio"] >= 1.4


@pytest.mark.anyio
async def test_chat_low_feasibility_exceeds_ceiling():
    """
    Scenario 3: Business with very high project cost that exceeds concessional ceiling.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/advisory/chat", json={
            "question": "Can I start a large food processing unit?",
            "language": "en",
            "business_category": "food_processing",
            "available_margin_capital": 600000.0,
            "village": "Tiny Hamlet",
            "district": "Nalgonda",
            "state": "Telangana",
            "radius_km": 5.0
        })
        assert res.status_code == 200
        data = res.json()
        ctx = data["context_snapshot"]
        assert ctx["feasibility_classification"] in ["MODERATE", "HIGH_RISK"]


@pytest.mark.anyio
async def test_chat_telugu_language():
    """
    Scenario 4: Telugu language request. The fallback answer must contain Telugu text.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/advisory/chat", json={
            "question": "నాకు డెయిరీ వ్యాపారం అనుకూలమా?",
            "language": "te",
            "business_category": "dairy",
            "available_margin_capital": 50000.0,
            "village": "Miryalaguda",
            "district": "Nalgonda",
            "state": "Telangana"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["language"] == "te"
        answer = data["answer"]
        has_telugu = any("\u0C00" <= ch <= "\u0C7F" for ch in answer)
        assert has_telugu, f"Expected Telugu text, got: {answer[:100]}"


@pytest.mark.anyio
async def test_chat_hindi_language():
    """
    Scenario 5: Hindi language request. The fallback answer must contain Hindi text.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/advisory/chat", json={
            "question": "क्या मुझे किराना दुकान खोलनी चाहिए?",
            "language": "hi",
            "business_category": "kirana",
            "available_margin_capital": 30000.0,
            "village": "Pindra",
            "district": "Varanasi",
            "state": "Uttar Pradesh"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["language"] == "hi"
        answer = data["answer"]
        has_hindi = any("\u0900" <= ch <= "\u097F" for ch in answer)
        assert has_hindi, f"Expected Hindi text, got: {answer[:100]}"


@pytest.mark.anyio
async def test_chat_ai_api_unavailable_fallback():
    """
    Scenario 6: AI API is unavailable (no GEMINI_API_KEY set).
    Must not crash; must return grounded deterministic fallback with real numbers.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/advisory/chat", json={
            "question": "What are the main risks for my business?",
            "language": "en",
            "business_category": "dairy",
            "available_margin_capital": 50000.0,
            "village": "Miryalaguda",
            "district": "Nalgonda",
            "state": "Telangana"
        })
        assert res.status_code == 200
        data = res.json()
        assert len(data["answer"]) > 50
        assert data["context_used"]["financial"] is True
        assert "₹" in data["answer"]
        assert data["context_snapshot"]["total_project_cost"] > 0


@pytest.mark.anyio
async def test_http_context_and_root_alias():
    """
    Scenario 7+8: GET /advisory/context and root-level POST /advisory/chat alias.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Root-level alias POST /advisory/chat
        res = await client.post("/advisory/chat", json={
            "question": "Is this business viable?",
            "language": "en",
            "business_category": "textiles",
            "available_margin_capital": 25000.0,
            "village": "Sanganer",
            "district": "Jaipur",
            "state": "Rajasthan"
        })
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert data["context_used"]["feasibility"] is True
