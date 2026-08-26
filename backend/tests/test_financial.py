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


def test_case_1_micro_finance_scheme():
    """CASE 1: Margin = ₹10,000 -> Project Cost = ₹1,00,000, Loan = ₹90,000, Micro Finance Scheme (6.5%, 36mo, 3mo morat)."""
    res = FinancialCalculationEngine.structure_from_available_margin(
        available_margin_capital=10000.0
    )
    assert res.eligible is True
    assert res.available_margin_capital == 10000.0
    assert res.total_feasible_project_cost == 100000.0
    assert res.maximum_loan_amount == 90000.0
    assert res.selected_scheme_tier == "Micro Finance Scheme"
    assert res.scheme_code == "SCA_MICRO_FINANCE"
    assert res.concessional_interest_rate_pct == 6.5
    assert res.loan_tenure_months == 36
    assert res.moratorium_months == 3
    assert res.ineligibility_reason is None
    assert len(res.quarterly_repayment_schedule) == 12
    # First quarter is moratorium (principal = 0)
    assert res.quarterly_repayment_schedule[0].is_moratorium is True
    assert res.quarterly_repayment_schedule[0].principal_repayment == 0.0


def test_case_2_term_loan_scheme_100k():
    """CASE 2: Margin = ₹1,00,000 -> Project Cost = ₹10,00,000, Loan = ₹9,00,000, Term Loan Scheme (8%, 84mo, 6mo morat)."""
    res = FinancialCalculationEngine.structure_from_available_margin(
        available_margin_capital=100000.0
    )
    assert res.eligible is True
    assert res.available_margin_capital == 100000.0
    assert res.total_feasible_project_cost == 1000000.0
    assert res.maximum_loan_amount == 900000.0
    assert res.selected_scheme_tier == "Term Loan Scheme"
    assert res.scheme_code == "SCA_TERM_LOAN"
    assert res.concessional_interest_rate_pct == 8.0
    assert res.loan_tenure_months == 84
    assert res.moratorium_months == 6
    assert res.ineligibility_reason is None
    assert len(res.quarterly_repayment_schedule) == 28
    # First 2 quarters are moratorium (principal = 0)
    assert res.quarterly_repayment_schedule[0].is_moratorium is True
    assert res.quarterly_repayment_schedule[1].is_moratorium is True
    assert res.quarterly_repayment_schedule[2].is_moratorium is False


def test_case_3_term_loan_scheme_boundary_500k():
    """CASE 3: Margin = ₹5,00,000 -> Project Cost = ₹50,00,000, Loan = ₹45,00,000, Term Loan Scheme (8%, 84mo, 6mo morat)."""
    res = FinancialCalculationEngine.structure_from_available_margin(
        available_margin_capital=500000.0
    )
    assert res.eligible is True
    assert res.available_margin_capital == 500000.0
    assert res.total_feasible_project_cost == 5000000.0
    assert res.maximum_loan_amount == 4500000.0
    assert res.selected_scheme_tier == "Term Loan Scheme"
    assert res.scheme_code == "SCA_TERM_LOAN"
    assert res.concessional_interest_rate_pct == 8.0
    assert res.loan_tenure_months == 84
    assert res.moratorium_months == 6
    assert res.ineligibility_reason is None
    assert len(res.quarterly_repayment_schedule) == 28


def test_case_4_ineligible_exceeds_ceiling_600k():
    """CASE 4: Margin = ₹6,00,000 -> Project Cost = ₹60,00,000 -> Not eligible (eligible=False, clear reason)."""
    res = FinancialCalculationEngine.structure_from_available_margin(
        available_margin_capital=600000.0
    )
    assert res.eligible is False
    assert res.available_margin_capital == 600000.0
    assert res.total_feasible_project_cost == 6000000.0
    assert res.maximum_loan_amount is None
    assert res.selected_scheme_tier is None
    assert res.scheme_code is None
    assert res.concessional_interest_rate_pct is None
    assert res.loan_tenure_months is None
    assert res.moratorium_months is None
    assert res.monthly_emi_amount is None
    assert res.quarterly_installment_amount is None
    assert res.quarterly_repayment_schedule == []
    assert res.ineligibility_reason is not None
    assert "exceeds" in res.ineligibility_reason.lower()


def test_margin_validation_zero_or_negative():
    """Verify margin <= 0 raises ValueError."""
    with pytest.raises(ValueError):
        FinancialCalculationEngine.structure_from_available_margin(available_margin_capital=0.0)
    with pytest.raises(ValueError):
        FinancialCalculationEngine.structure_from_available_margin(available_margin_capital=-5000.0)



