import pytest
from app.models.user import SocialCategoryEnum
from app.services.financial_engine import FinancialCalculationEngine


def test_project_cost_calculation():
    """Verify total project cost calculation with normal and seasonal working capital buffer."""
    # Normal 3 months OPEX
    cost_normal = FinancialCalculationEngine.calculate_project_cost(
        capex=300000.0,
        monthly_opex=20000.0,
        working_capital_months=3,
        has_seasonal_dip=False
    )
    assert cost_normal["total_capex"] == 300000.0
    assert cost_normal["working_capital_buffer"] == 60000.0
    assert cost_normal["total_project_cost"] == 360000.0

    # Seasonal 5 months OPEX (3 + 2 extra buffer)
    cost_seasonal = FinancialCalculationEngine.calculate_project_cost(
        capex=300000.0,
        monthly_opex=20000.0,
        working_capital_months=3,
        has_seasonal_dip=True
    )
    assert cost_seasonal["working_capital_buffer"] == 100000.0
    assert cost_seasonal["total_project_cost"] == 400000.0


def test_capital_structure_pmegp_subsidies():
    """Verify PMEGP subsidy calculations for general vs special rural categories."""
    total_cost = 400000.0

    # General Category in Rural: 10% margin, 25% subsidy
    general_cap = FinancialCalculationEngine.calculate_capital_structure(
        total_project_cost=total_cost,
        user_margin_available=50000.0,
        scheme_code="PMEGP",
        category=SocialCategoryEnum.GENERAL,
        is_rural=True
    )
    assert general_cap["user_margin_amount"] == 40000.0  # 10% of 400k
    assert general_cap["subsidy_amount_eligible"] == 100000.0  # 25% of 400k
    assert general_cap["net_bank_loan_required"] == 260000.0  # 400k - 40k - 100k

    # Special Category (SC/ST/Women/OBC) in Rural: 5% margin, 35% subsidy
    special_cap = FinancialCalculationEngine.calculate_capital_structure(
        total_project_cost=total_cost,
        user_margin_available=50000.0,
        scheme_code="PMEGP",
        category=SocialCategoryEnum.WOMEN_ENTREPRENEUR,
        is_rural=True
    )
    assert special_cap["user_margin_amount"] == 20000.0  # 5% of 400k
    assert special_cap["subsidy_amount_eligible"] == 140000.0  # 35% of 400k
    assert special_cap["net_bank_loan_required"] == 240000.0  # 400k - 20k - 140k


def test_emi_calculation():
    """Verify bank EMI equation."""
    # Principal ₹2,00,000, 8.5% annual rate, 60 months tenure
    emi = FinancialCalculationEngine.calculate_emi(
        principal=200000.0,
        annual_rate=8.5,
        tenure_months=60
    )
    # Expected EMI is ~ ₹4,103.31
    assert 4000.0 < emi < 4200.0


def test_profitability_and_dscr():
    """Verify Net profit, DSCR, BEP, and ROI metrics."""
    result = FinancialCalculationEngine.calculate_profitability_and_ratios(
        total_project_cost=350000.0,
        total_capex=300000.0,
        monthly_revenue=38000.0,
        monthly_opex=20000.0,
        monthly_emi=3900.0,
        annual_rate=8.5
    )
    # Monthly gross = 18,000
    assert result["monthly_gross_profit"] == 18000.0
    # Monthly dep (10% of 300k / 12) = 2,500
    # Net profit = 18,000 - 3,900 - 2,500 = 11,600
    assert result["monthly_net_profit"] == 11600.0
    # DSCR = (18000 * 12) / (3900 * 12) = 18000 / 3900 = 4.62
    assert result["dscr_ratio"] >= 4.0
    assert result["is_bankable"] is True


def test_full_financial_plan():
    """Verify end-to-end financial plan execution."""
    plan = FinancialCalculationEngine.compute_full_financial_plan(
        capex=350000.0,
        monthly_opex=22000.0,
        monthly_revenue=38000.0,
        user_margin_available=50000.0,
        category=SocialCategoryEnum.OBC,
        is_rural=True
    )
    assert plan.total_project_cost > 350000.0
    assert plan.subsidy_pct == 35.0
    assert plan.monthly_emi_amount > 0
    assert plan.dscr_ratio > 1.5
    assert plan.cash_flow_5yr["projection_horizon_years"] == 5

