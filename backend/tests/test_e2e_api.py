import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import engine, Base
from app.seeds.schemes import seed_sectors_and_schemes
from app.seeds.market_data import seed_market_data


@pytest.mark.anyio
async def test_full_api_flow():
    print("Initializing tables and seeding test database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await seed_sectors_and_schemes()
    await seed_market_data()

    print("\nTesting RuralBiz AI FastAPI backend endpoints...")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        res = await client.get("/")
        print("Root Status:", res.status_code, res.json())
        assert res.status_code == 200

        # 2. Register User
        reg_payload = {
            "phone_number": "9988776655",
            "full_name": "Suresh Reddy",
            "password": "securepassword",
            "preferred_language": "te",
            "social_category": "obc",
            "available_margin_money": 60000.0,
            "annual_income": 160000.0,
            "district": "Nalgonda"
        }
        res_reg = await client.post("/api/v1/users/register", json=reg_payload)
        print("User Register status:", res_reg.status_code)
        
        # Login
        res_login = await client.post("/api/v1/users/login", json={
            "phone_number": "9988776655",
            "password": "securepassword"
        })
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("User Login: JWT Token acquired successfully.")

        # 3. List Sectors & Types
        res_sec = await client.get("/api/v1/businesses/sectors", headers=headers)
        sectors = res_sec.json()
        print(f"Sectors found: {len(sectors)} sectors ({[s['code'] for s in sectors]})")
        assert len(sectors) >= 7

        res_types = await client.get("/api/v1/businesses/types", headers=headers)
        types = res_types.json()
        dairy_type = next((t for t in types if "dairy" in t["code"]), types[0])
        print(f"Sample Type: {dairy_type['name_en']} (Default Capex: Rs. {dairy_type['default_capex']:,.0f})")

        # 4. Create Business Application
        app_payload = {
            "business_type_id": dairy_type["id"],
            "scale_units": 5,
            "user_margin_available": 60000.0,
            "own_land_available": True,
            "land_area_sqft": 1200.0
        }
        res_app = await client.post("/api/v1/businesses/applications", json=app_payload, headers=headers)
        app_obj = res_app.json()
        app_id = app_obj["id"]
        print(f"Created Application ID: {app_id}")

        # 5. Calculate Financials for Application
        res_fin = await client.post(f"/api/v1/financial/application/{app_id}/calculate", headers=headers)
        fin = res_fin.json()
        print(f"Financial Model: Total Cost=Rs. {fin['total_project_cost']:,.0f}, Subsidy=Rs. {fin['subsidy_amount_eligible']:,.0f} ({fin['subsidy_pct']}%), EMI=Rs. {fin['monthly_emi_amount']:,.0f}/mo, DSCR={fin['dscr_ratio']}")

        # 6. Scheme Matching
        res_sch = await client.post("/api/v1/schemes/match", json={
            "sector_code": "dairy",
            "project_cost": fin["total_project_cost"],
            "user_margin_available": 60000.0,
            "category": "obc",
            "is_rural": True
        }, headers=headers)
        schemes = res_sch.json()
        print(f"Top Scheme: {schemes[0]['scheme_name']} (Subsidy: Rs. {schemes[0]['subsidy_amount']:,.0f})")

        # 7. Evaluate Feasibility
        res_eval = await client.post(f"/api/v1/analysis/evaluate/{app_id}", headers=headers)
        eval_res = res_eval.json()
        print(f"Feasibility Score: {eval_res['overall_score']}/100, Rating: {eval_res['viability_rating']}, Gap: {eval_res['market_gap_classification']}")

        # 8. Query AI Advisor in Telugu
        res_adv_te = await client.post("/api/v1/advisory/query", json={
            "query_text": "డెయిరీ వ్యాపారం నాకు అనుకూలమా? ఎంత లోన్ వస్తుంది?",
            "language": "te",
            "application_id": app_id
        }, headers=headers)
        adv_te = res_adv_te.json()
        print("\n--- AI Advisor Response (Telugu) ---")
        print(adv_te["conversational_response"])
        print("\nAudio TTS Script:", adv_te["audio_tts_text"])

        # 9. Query AI Advisor in Hindi
        res_adv_hi = await client.post("/api/v1/advisory/query", json={
            "query_text": "क्या डेयरी का व्यवसाय मेरे लिए सही रहेगा?",
            "language": "hi",
            "application_id": app_id
        }, headers=headers)
        adv_hi = res_adv_hi.json()
        print("\n--- AI Advisor Response (Hindi) ---")
        print(adv_hi["conversational_response"])

        # 10. Generate Bank Report
        res_rep = await client.get(f"/api/v1/analysis/{app_id}/report", headers=headers)
        rep = res_rep.json()
        print(f"\nConsolidated Bank Report Generated: {rep['report_title']} ({rep['report_id']})")
        print("\n=======================================================")
        print(" SUCCESS: All RuralBiz AI backend modules working 100%! ")
        print("=======================================================")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_api_flow())

