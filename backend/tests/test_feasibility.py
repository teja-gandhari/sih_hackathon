import pytest
from app.models.user import SocialCategoryEnum
from app.services.financial_engine import FinancialCalculationEngine
from app.services.scheme_engine import SchemeEligibilityEngine
from app.services.feasibility_engine import FeasibilityScoringEngine


def test_purchasing_power_fit_essential_vs_luxury():
    """Verify purchasing power score differentiates low-ticket essentials from high-ticket items."""
    # Essential milk purchase (₹45 ticket vs ₹300 daily wage)
    score_milk, msg_milk = FeasibilityScoringEngine.calculate_purchasing_power_fit(
        typical_ticket_size=45.0,
        mgnrega_daily_wage=300.0,
        household_income=14000.0,
        purchasing_power_tier="lower_middle",
        requires_daily_footfall=False,
        is_export_or_wholesale=True
    )
    assert score_milk >= 85.0

    # Unaffordable luxury item in low income village (₹450 ticket vs ₹300 daily wage)
    score_luxury, msg_luxury = FeasibilityScoringEngine.calculate_purchasing_power_fit(
        typical_ticket_size=450.0,
        mgnrega_daily_wage=300.0,
        household_income=10000.0,
        purchasing_power_tier="low",
        requires_daily_footfall=True,
        is_export_or_wholesale=False
    )
    assert score_luxury < 40.0


def test_unserved_vs_unviable_classifier():
    """Verify zero competition in low purchasing power village triggers 'unviable_purchasing_power_gap'."""
    classification, informal_w, seasonal_w, cluster_s = FeasibilityScoringEngine.classify_market_gap(
        formal_competitors=0,
        informal_competitors=0,
        purchasing_power_score=30.0,  # Unaffordable
        demand_index=6.0,
        cluster_failure_rate=25.0
    )
    assert classification == "unviable_purchasing_power_gap"
    assert "caution" in informal_w or "caution" in classification or "unviable" in classification


def test_viable_and_unserved_market():
    """Verify high purchasing power + low competition yields 'viable_and_unserved'."""
    classification, _, _, _ = FeasibilityScoringEngine.classify_market_gap(
        formal_competitors=1,
        informal_competitors=1,
        purchasing_power_score=85.0,
        demand_index=8.5,
        cluster_failure_rate=10.0
    )
    assert classification == "viable_and_unserved"


def test_end_to_end_feasibility_evaluation():
    """Verify full feasibility evaluation workflow produces composite score and grounded SWOT."""
    financials = FinancialCalculationEngine.compute_full_financial_plan(
        capex=350000.0,
        monthly_opex=22000.0,
        monthly_revenue=38000.0,
        user_margin_available=50000.0,
        category=SocialCategoryEnum.OBC,
        is_rural=True
    )

    schemes = SchemeEligibilityEngine.evaluate_eligibility(
        sector_code="dairy",
        project_cost=financials.total_project_cost,
        user_margin_available=50000.0,
        category=SocialCategoryEnum.OBC,
        is_rural=True
    )

    market_data = {
        "demand_index": 8.5,
        "formal_competitor_count": 2,
        "estimated_informal_competitor_count": 4,
        "mgnrega_daily_wage_rate": 300.0,
        "average_monthly_household_income": 15000.0,
        "purchasing_power_tier": "lower_middle",
        "raw_material_availability_score": 8.5,
        "infrastructure_score": 7.5,
        "regional_cluster_failure_rate_pct": 12.0,
        "data_confidence_level": "moderate_proxy"
    }

    business_type = {
        "name_en": "5 Murrah Buffalo Dairy Unit",
        "typical_ticket_size": 45.0,
        "is_export_or_wholesale": True,
        "requires_daily_footfall": False
    }

    result = FeasibilityScoringEngine.evaluate_feasibility(
        application_id="test-app-1",
        financials=financials,
        matched_schemes=schemes,
        market_data=market_data,
        business_type=business_type
    )

    assert result.overall_score >= 70.0
    assert result.viability_rating in ["high_feasibility", "moderate_feasibility"]
    assert result.swot_analysis is not None
    assert len(result.swot_analysis.strengths) > 0
    assert len(result.key_recommendations) > 0

