"""
Tests for Final Report and Application Summary Module
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base, AsyncSessionLocal
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
async def test_get_application_summary_invalid_id():
    """Test GET /api/v1/reports/{id}/summary with non-existent ID -> 404"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/reports/non-existent-id/summary")
        assert res.status_code == 404


@pytest.mark.anyio
async def test_get_application_pdf_invalid_id():
    """Test GET /api/v1/reports/{id}/pdf with non-existent ID -> 404"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/reports/non-existent-id/pdf")
        assert res.status_code == 404


@pytest.mark.anyio
async def test_reports_with_valid_application():
    """Create an application and test summary and pdf"""
    from app.models.application import BusinessApplication, FinancialPlan, FeasibilityAssessment
    from app.models.user import User
    from app.models.business import BusinessType, BusinessSector
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # Fetch existing seeded business type
        res = await db.execute(select(BusinessType).where(BusinessType.code == "dairy"))
        bt = res.scalars().first()
        if not bt:
            pytest.fail("Seeded BusinessType 'dairy' not found")

        import uuid
        uid = f"user_{uuid.uuid4().hex[:8]}"
        phone = f"999{uuid.uuid4().hex[:7]}"
        app_id = f"app_{uuid.uuid4().hex[:8]}"

        # Create user
        user = User(
            id=uid, phone_number=phone, hashed_password="fake", full_name="Test User",
            state="Telangana", district="Nalgonda", village="Miryalaguda"
        )
        db.add(user)
        await db.commit()
        
        # Create application
        app_obj = BusinessApplication(
            id=app_id, user_id=uid, business_type_id=bt.id,
            user_margin_available=50000.0
        )
        db.add(app_obj)
        
        # Create partial financial
        fp = FinancialPlan(
            application_id=app_id, total_project_cost=350000.0,
            net_bank_loan_required=200000.0, matched_scheme_code="PMEGP",
            monthly_emi_amount=4000.0, subsidy_amount_eligible=100000.0
        )
        db.add(fp)
        
        # Create feasibility
        fa = FeasibilityAssessment(
            application_id=app_id, overall_score=85.0, viability_rating="high_feasibility",
            market_demand_score=80.0, financial_viability_score=90.0,
            risk_score=20.0,
            swot_analysis={"opportunities": ["Great demand"], "threats": ["Summer heat"]},
            key_recommendations=["Proceed with dairy farm"]
        )
        db.add(fa)
        
        await db.commit()

    # 1. Test Summary JSON
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/api/v1/reports/{app_id}/summary")
        assert res.status_code == 200
        data = res.json()
        assert data["application_id"] == app_id
        assert data["business_profile"]["business_category"] == "Dairy"
        assert data["financial_summary"]["project_cost"] == 350000.0
        assert data["scheme_summary"]["scheme_name"] == "PMEGP"
        assert data["feasibility_summary"]["overall_score"] == 85.0
        assert "Great demand" in data["key_opportunities"]
        
    # 2. Test PDF Generation
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/api/v1/reports/{app_id}/pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "attachment" in res.headers["content-disposition"]
        assert f"RuralBiz_AI_Feasibility_Report_{app_id}.pdf" in res.headers["content-disposition"]
        # Basic check to ensure PDF binary signature
        assert res.content.startswith(b"%PDF-")
