import pytest
from app.models.user import SocialCategoryEnum
from app.services.scheme_engine import SchemeEligibilityEngine


def test_scheme_matching_dairy_rural_women():
    """Verify that a rural woman entrepreneur in dairy gets PMEGP with 35% subsidy."""
    schemes = SchemeEligibilityEngine.evaluate_eligibility(
        sector_code="dairy",
        project_cost=350000.0,
        user_margin_available=50000.0,
        category=SocialCategoryEnum.WOMEN_ENTREPRENEUR,
        is_rural=True
    )
    assert len(schemes) > 0
    top_scheme = schemes[0]
    assert top_scheme.scheme_code == "PMEGP"
    assert top_scheme.eligible is True
    assert top_scheme.subsidy_percentage == 35.0
    assert top_scheme.subsidy_amount == 122500.0
    assert top_scheme.margin_required_percentage == 5.0


def test_scheme_matching_food_processing_pmfme():
    """Verify PMFME scheme availability for food processing."""
    schemes = SchemeEligibilityEngine.evaluate_eligibility(
        sector_code="food_processing",
        project_cost=280000.0,
        user_margin_available=40000.0,
        category=SocialCategoryEnum.GENERAL,
        is_rural=True
    )
    pmfme = next((s for s in schemes if s.scheme_code == "PMFME"), None)
    assert pmfme is not None
    assert pmfme.eligible is True
    assert pmfme.subsidy_percentage == 35.0


def test_scheme_cost_ceiling_rejection():
    """Verify that excessive project cost is correctly rejected for small scale schemes."""
    schemes = SchemeEligibilityEngine.evaluate_eligibility(
        sector_code="retail",
        project_cost=800000.0,  # ₹8 Lakhs exceeds Mudra Kishore limit (₹5 Lakhs)
        user_margin_available=100000.0,
        category=SocialCategoryEnum.GENERAL,
        is_rural=True
    )
    mudra_kishore = next((s for s in schemes if s.scheme_code == "MUDRA_KISHORE"), None)
    assert mudra_kishore is not None
    assert mudra_kishore.eligible is False

