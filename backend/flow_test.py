"""
RuralBiz AI — Full Flow Integration Test (Standalone, Human-Readable Output)

Flow:
  Register / Login
      ↓
  Get Business Types + Location IDs
      ↓
  Create Business Application
      ↓
  Calculate Financials
      ↓
  Match Government Scheme
      ↓
  Get Market Data
      ↓
  Evaluate Feasibility
      ↓
  AI Advisory (Telugu + Hindi + English)
      ↓
  Generate Bank Report

Run:
  cd d:\sih\backend
  python flow_test.py
"""

import os
import sys
import asyncio
import json

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base
from app.seeds.schemes import seed_sectors_and_schemes
from app.seeds.market_data import seed_market_data

# ─── Utilities ────────────────────────────────────────────────────────────────
PASS = "✅ PASS"
FAIL = "❌ FAIL"

def divider(title=""):
    w = 66
    if title:
        pad = (w - len(title) - 2) // 2
        print(f"\n{'─' * pad} {title} {'─' * pad}")
    else:
        print("─" * w)

def status(code, expected=200):
    if code == expected:
        return f"  {PASS}  HTTP {code}"
    return f"  {FAIL}  HTTP {code} (expected {expected})"

def rupees(amount):
    return f"₹{amount:,.0f}"

# ─── Main Flow ────────────────────────────────────────────────────────────────
async def run_flow():
    # Initialize database and seed data
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_sectors_and_schemes()
    await seed_market_data()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # ── Step 0: Health Check ──────────────────────────────────────────────
        divider("STEP 0 · Health Check")
        res = await client.get("/")
        data = res.json()
        print(status(res.status_code))
        print(f"  App: {data['app']}  v{data['version']}")
        print(f"  Languages: {data['supported_languages']}")
        assert res.status_code == 200

        # ── Step 1: Register User ─────────────────────────────────────────────
        divider("STEP 1 · Register User")
        reg_payload = {
            "phone_number": "9876543210",
            "full_name": "Lakshmi Devi",
            "password": "test@12345",
            "preferred_language": "te",
            "social_category": "obc",
            "available_margin_money": 50000.0,
            "annual_income": 120000.0,
            "district": "Nalgonda"
        }
        # Use a unique phone to avoid conflicts on re-runs; fallback if already exists
        import random, string
        phone = "98" + "".join(random.choices(string.digits, k=8))
        reg_payload["phone_number"] = phone
        res = await client.post("/api/v1/users/register", json=reg_payload)
        print(status(res.status_code, expected=201))
        user_data = res.json() if res.status_code in (200, 201) else {}
        if res.status_code in (200, 201):
            print(f"  User Created: {user_data.get('full_name', '—')} | Phone: {phone} | Category: {user_data.get('social_category', '—')}")
        else:
            print(f"  ℹ️  (Using phone {phone[:4]}...{phone[-4:]})")

        # Login — always use a known seeded user (or the one we just created)
        # If registration failed, fall back to a previously created user
        login_phone = phone if res.status_code in (200, 201) else "9876543210"
        login_pwd   = reg_payload["password"]

        # ── Step 2: Login ─────────────────────────────────────────────────────
        divider("STEP 2 · Login")
        res = await client.post("/api/v1/users/login", json={
            "phone_number": login_phone,
            "password": login_pwd
        })
        print(status(res.status_code))
        login_data = res.json()
        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  JWT Token: {token[:40]}...")
        assert res.status_code == 200

        # ── Step 3: Get /me ───────────────────────────────────────────────────
        divider("STEP 3 · Get Current User Profile (/me)")
        res = await client.get("/api/v1/users/me", headers=headers)
        print(status(res.status_code))
        me = res.json()
        print(f"  Name: {me['full_name']}")
        print(f"  Phone: {me['phone_number']}")
        print(f"  Language: {me['preferred_language']}")
        print(f"  Social Category: {me['social_category']}")
        print(f"  Margin Available: {rupees(me['available_margin_money'])}")
        assert res.status_code == 200

        # ── Step 4: List Business Sectors ─────────────────────────────────────
        divider("STEP 4 · List Business Sectors")
        res = await client.get("/api/v1/businesses/sectors", headers=headers)
        print(status(res.status_code))
        sectors = res.json()
        print(f"  Total Sectors: {len(sectors)}")
        for s in sectors:
            print(f"    → [{s['code']}] {s['name_en']}")
        assert len(sectors) >= 7

        # ── Step 5: Get Business Types ────────────────────────────────────────
        divider("STEP 5 · Get Business Types (Dairy Sector)")
        res = await client.get("/api/v1/businesses/types", headers=headers)
        print(status(res.status_code))
        types = res.json()
        dairy_type = next((t for t in types if "dairy" in t["code"].lower()), types[0])
        print(f"  Total Types Available: {len(types)}")
        print(f"  Selected: [{dairy_type['code']}] {dairy_type['name_en']}")
        print(f"  Default CAPEX:    {rupees(dairy_type['default_capex'])}")
        print(f"  Default OPEX/mo:  {rupees(dairy_type['default_monthly_opex'])}")
        print(f"  Expected Revenue: {rupees(dairy_type['default_monthly_revenue'])}")
        print(f"  Min Power Tier:   {dairy_type['min_purchasing_power_tier']}")
        assert res.status_code == 200

        # ── Step 6: Get District / Location IDs ───────────────────────────────
        divider("STEP 6 · Get Location (Districts)")
        res = await client.get("/api/v1/market/districts", headers=headers)
        print(status(res.status_code))
        districts = res.json()
        print(f"  Districts Available: {len(districts)}")
        for d in districts:
            pop = d.get('population')
            pop_str = f"{pop:,}" if isinstance(pop, int) else "N/A"
            print(f"    → {d['district_name']} ({d['state_name']}) — Population: {pop_str}")
        assert res.status_code == 200

        # ── Step 7: Create Business Application ───────────────────────────────
        divider("STEP 7 · Create Business Application")
        app_payload = {
            "business_type_id": dairy_type["id"],
            "scale_units": 5,
            "user_margin_available": 50000.0,
            "own_land_available": True,
            "land_area_sqft": 800.0
        }
        res = await client.post("/api/v1/businesses/applications", json=app_payload, headers=headers)
        print(status(res.status_code, expected=201))
        app_obj = res.json()
        app_id = app_obj["id"]
        print(f"  Application ID: {app_id}")
        print(f"  Business Type:  {dairy_type['name_en']}")
        print(f"  Scale Units:    {app_payload['scale_units']}")
        print(f"  Own Land:       {'Yes' if app_payload['own_land_available'] else 'No'}")
        print(f"  User Margin:    {rupees(app_payload['user_margin_available'])}")
        assert res.status_code in (200, 201)

        # ── Step 8: Calculate Financials ──────────────────────────────────────
        divider("STEP 8 · Calculate Financials")
        res = await client.post(f"/api/v1/financial/application/{app_id}/calculate", headers=headers)
        print(status(res.status_code))
        fin = res.json()
        print(f"  Total CAPEX:          {rupees(fin['total_capex'])}")
        print(f"  Working Capital Buf:  {rupees(fin['working_capital_buffer'])}")
        print(f"  Total Project Cost:   {rupees(fin['total_project_cost'])}")
        print(f"  Promoter Margin:      {rupees(fin['user_margin_amount'])} ({fin['user_margin_pct']}%)")
        print(f"  Government Subsidy:   {rupees(fin['subsidy_amount_eligible'])} ({fin['subsidy_pct']}%) → [{fin['matched_scheme_code']}]")
        print(f"  Net Bank Loan:        {rupees(fin['net_bank_loan_required'])}")
        print(f"  Monthly EMI:          {rupees(fin['monthly_emi_amount'])} @ {fin['annual_interest_rate']}% p.a.")
        print(f"  Monthly Revenue:      {rupees(fin['projected_monthly_revenue'])}")
        print(f"  Monthly Net Profit:   {rupees(fin['monthly_net_profit'])}")
        print(f"  DSCR Ratio:           {fin['dscr_ratio']} (min required: 1.40) — {'Bankable ✅' if fin['is_bankable'] else 'NOT Bankable ❌'}")
        print(f"  ROI:                  {fin['roi_percentage']}%")
        print(f"  Break-Even:           {fin['break_even_months']} months")
        print(f"  Payback Period:       {fin['payback_period_years']} years")
        assert res.status_code == 200

        # ── Step 9: Match Government Schemes ──────────────────────────────────
        divider("STEP 9 · Match Government Schemes")
        res = await client.post("/api/v1/schemes/match", json={
            "sector_code": "dairy",
            "project_cost": fin["total_project_cost"],
            "user_margin_available": 50000.0,
            "category": "obc",
            "is_rural": True
        }, headers=headers)
        print(status(res.status_code))
        schemes = res.json()
        eligible = [s for s in schemes if s.get("eligible")]
        print(f"  Total Schemes Evaluated: {len(schemes)}")
        print(f"  Eligible Schemes: {len(eligible)}")
        for s in schemes:
            mark = "✅" if s["eligible"] else "❌"
            print(f"    {mark} [{s['scheme_code']}] {s['scheme_name']}")
            if s["eligible"]:
                print(f"         Subsidy: {rupees(s['subsidy_amount'])} ({s['subsidy_percentage']}%) | Rate: {s['estimated_interest_rate']}%")
        assert res.status_code == 200

        # ── Step 10: Get Market Indicators ────────────────────────────────────
        divider("STEP 10 · Get Market / Hyper-Local Indicators")
        res = await client.get("/api/v1/market/indicators?sector_code=dairy", headers=headers)
        print(status(res.status_code))
        market = res.json()
        print(f"  Sector:                 {market.get('sector', 'dairy')}")
        print(f"  Demand Index:           {market.get('demand_index', 'N/A')}/100")
        print(f"  Formal Competitors:     {market.get('formal_competitor_count', 'N/A')}")
        print(f"  Informal Competitors:   ~{market.get('informal_competitor_estimate', 'N/A')}")
        print(f"  MGNREGA Wage (proxy):   ₹{market.get('mgnrega_daily_wage_proxy', 'N/A')}/day")
        print(f"  Purchasing Power Tier:  {market.get('purchasing_power_tier', 'N/A')}")
        print(f"  Data Confidence:        {market.get('data_confidence_level', 'N/A')}")
        assert res.status_code == 200

        # ── Step 11: Evaluate Feasibility ─────────────────────────────────────
        divider("STEP 11 · Evaluate Feasibility")
        res = await client.post(f"/api/v1/analysis/evaluate/{app_id}", headers=headers)
        print(status(res.status_code))
        ev = res.json()
        print(f"  Overall Score:          {ev['overall_score']}/100")
        print(f"  Viability Rating:       {ev['viability_rating']}")
        print(f"  Market Gap:             {ev['market_gap_classification']}")
        print(f"  Purchasing Power Fit:   {ev.get('purchasing_power_fit_score', 'N/A')}/100")
        print(f"  Financial Viability:    {ev.get('financial_viability_score', 'N/A')}/100")
        print(f"  Market Demand Score:    {ev.get('market_demand_score', 'N/A')}/100")
        print(f"  Resource Readiness:     {ev.get('resource_readiness_score', 'N/A')}/100")
        print(f"  Data Confidence Level:  {ev.get('data_confidence_level', 'N/A')}")
        
        if ev.get("informal_competition_warning"):
            print(f"  ⚠️  Informal Warning:   {ev['informal_competition_warning']}")
        if ev.get("seasonal_cashflow_warning"):
            print(f"  ⚠️  Seasonal Warning:   {ev['seasonal_cashflow_warning']}")
            
        print(f"\n  SWOT Summary:")
        swot = ev.get("swot_analysis", {})
        if isinstance(swot, dict):
            for k, v in swot.items():
                if isinstance(v, list):
                    for item in v:
                        print(f"    [{k.upper()}] {item}")
        if ev.get("key_recommendations"):
            print(f"\n  💡 Recommendations:")
            for rec in ev["key_recommendations"]:
                print(f"    → {rec}")
        assert res.status_code == 200

        # ── Step 12: AI Advisory — Telugu ─────────────────────────────────────
        divider("STEP 12 · AI Advisory — Telugu (తెలుగు)")
        res = await client.post("/api/v1/advisory/query", json={
            "query_text": "డెయిరీ వ్యాపారం నాకు అనుకూలమా? ఎంత లోన్ వస్తుంది?",
            "language": "te",
            "application_id": app_id
        }, headers=headers)
        print(status(res.status_code))
        adv = res.json()
        print(f"\n  Query: {adv.get('query_text', '—')}")
        print(f"\n  Response:\n  {adv['conversational_response']}")
        print(f"\n  🔊 TTS Script:\n  {adv.get('audio_tts_text', '—')}")
        assert res.status_code == 200

        # ── Step 13: AI Advisory — Hindi ──────────────────────────────────────
        divider("STEP 13 · AI Advisory — Hindi (हिंदी)")
        res = await client.post("/api/v1/advisory/query", json={
            "query_text": "क्या डेयरी व्यवसाय मेरे लिए सही है? कितना लोन मिलेगा?",
            "language": "hi",
            "application_id": app_id
        }, headers=headers)
        print(status(res.status_code))
        adv = res.json()
        print(f"\n  Query: {adv.get('query_text', '—')}")
        print(f"\n  Response:\n  {adv['conversational_response']}")
        assert res.status_code == 200

        # ── Step 14: AI Advisory — English ────────────────────────────────────
        divider("STEP 14 · AI Advisory — English")
        res = await client.post("/api/v1/advisory/query", json={
            "query_text": "Is a dairy business viable for me? How much loan and subsidy am I eligible for?",
            "language": "en",
            "application_id": app_id
        }, headers=headers)
        print(status(res.status_code))
        adv = res.json()
        print(f"\n  Query: {adv.get('query_text', '—')}")
        print(f"\n  Response:\n  {adv['conversational_response']}")
        assert res.status_code == 200

        # ── Step 15: Generate Bank Report ─────────────────────────────────────
        divider("STEP 15 · Generate Consolidated Bank Report")
        res = await client.get(f"/api/v1/analysis/{app_id}/report", headers=headers)
        print(status(res.status_code))
        rep = res.json()
        print(f"  Report ID:      {rep['report_id']}")
        print(f"  Report Title:   {rep['report_title']}")
        print(f"  Applicant:      {rep['entrepreneur_profile']['name']}")
        print(f"  Category:       {rep['entrepreneur_profile']['category']}")
        print(f"  Enterprise:     {rep['enterprise_profile']['business_name']} ({rep['enterprise_profile']['scale']})")
        print(f"\n  === Financial Summary ===")
        fs = rep.get("financial_summary", {})
        for k, v in fs.items():
            print(f"    {k}: {v}")
            
        print(f"\n  === Market & Viability ===")
        mv = rep.get("market_and_viability", {})
        for k, v in mv.items():
            print(f"    {k}: {v}")
        assert res.status_code == 200

        # ── Final Summary ──────────────────────────────────────────────────────
        divider()
        print()
        print("  ╔═══════════════════════════════════════════════════════╗")
        print("  ║  ✅  ALL 15 STEPS PASSED — RuralBiz AI Backend OK!  ║")
        print("  ╚═══════════════════════════════════════════════════════╝")
        print()


if __name__ == "__main__":
    asyncio.run(run_flow())
