import math
from typing import Dict, Any, List
from app.models.user import SocialCategoryEnum
from app.schemas.financial import FinancialBreakdownResponse


class FinancialCalculationEngine:
    """
    Deterministic Financial Engine for Rural Micro-Enterprises.
    Implements standard banking equations for project cost, margin, subsidy,
    EMI, DSCR, BEP, and 5-year cash flows with seasonal working capital adjustments.
    """

    @staticmethod
    def calculate_project_cost(
        capex: float,
        monthly_opex: float,
        working_capital_months: int = 3,
        has_seasonal_dip: bool = False
    ) -> Dict[str, float]:
        """
        Calculates total project cost with required working capital buffer.
        In rural seasonal areas, working capital is extended to 4-5 months.
        """
        effective_wc_months = working_capital_months + (2 if has_seasonal_dip else 0)
        working_capital_buffer = monthly_opex * effective_wc_months
        total_project_cost = capex + working_capital_buffer

        return {
            "total_capex": round(capex, 2),
            "total_opex_monthly": round(monthly_opex, 2),
            "effective_wc_months": effective_wc_months,
            "working_capital_buffer": round(working_capital_buffer, 2),
            "total_project_cost": round(total_project_cost, 2)
        }

    @staticmethod
    def calculate_capital_structure(
        total_project_cost: float,
        user_margin_available: float,
        scheme_code: str = "PMEGP",
        category: SocialCategoryEnum = SocialCategoryEnum.GENERAL,
        is_rural: bool = True
    ) -> Dict[str, float]:
        """
        Calculates required user margin, government subsidy, and net bank loan.
        """
        is_special = category in [
            SocialCategoryEnum.SC,
            SocialCategoryEnum.ST,
            SocialCategoryEnum.OBC,
            SocialCategoryEnum.WOMEN_ENTREPRENEUR,
            SocialCategoryEnum.MINORITY
        ]

        # Standard promoter margin requirements: 5% for special categories, 10% for general
        min_margin_pct = 5.0 if is_special else 10.0
        user_margin_amount = (min_margin_pct / 100.0) * total_project_cost
        user_margin_pct = min_margin_pct

        # Scheme Subsidies (PMEGP / PMFME standard benchmarks)
        if scheme_code.upper() in ["PMEGP", "PMFME"]:
            if is_rural:
                subsidy_pct = 35.0 if is_special else 25.0
            else:
                subsidy_pct = 25.0 if is_special else 15.0
            
            # PMEGP Max Subsidy Cap (₹12.5 Lakhs for Manufacturing, ₹6.25 Lakhs for Service)
            max_subsidy_cap = 1250000.0
            subsidy_amount = min((subsidy_pct / 100.0) * total_project_cost, max_subsidy_cap)
        elif scheme_code.upper().startswith("MUDRA"):
            subsidy_pct = 0.0
            subsidy_amount = 0.0
        elif scheme_code.upper() == "STANDUP_INDIA":
            subsidy_pct = 15.0 if is_special else 0.0
            subsidy_amount = (subsidy_pct / 100.0) * total_project_cost
        else:
            subsidy_pct = 25.0 if is_rural else 15.0
            subsidy_amount = (subsidy_pct / 100.0) * total_project_cost

        # Net Bank Loan Required
        net_bank_loan = max(0.0, total_project_cost - user_margin_amount - subsidy_amount)

        return {
            "user_margin_amount": round(user_margin_amount, 2),
            "user_margin_pct": round(user_margin_pct, 2),
            "subsidy_amount_eligible": round(subsidy_amount, 2),
            "subsidy_pct": round(subsidy_pct, 2),
            "net_bank_loan_required": round(net_bank_loan, 2),
            "matched_scheme_code": scheme_code
        }

    @staticmethod
    def calculate_emi(
        principal: float,
        annual_rate: float = 8.5,
        tenure_months: int = 60
    ) -> float:
        """
        Calculates standard bank Equated Monthly Installment (EMI).
        EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        """
        if principal <= 0 or tenure_months <= 0:
            return 0.0
        
        monthly_rate = (annual_rate / 12.0) / 100.0
        if monthly_rate == 0:
            return round(principal / tenure_months, 2)
            
        emi = (principal * monthly_rate * math.pow(1 + monthly_rate, tenure_months)) / (
            math.pow(1 + monthly_rate, tenure_months) - 1
        )
        return round(emi, 2)

    @staticmethod
    def calculate_profitability_and_ratios(
        total_project_cost: float,
        total_capex: float,
        monthly_revenue: float,
        monthly_opex: float,
        monthly_emi: float,
        annual_rate: float = 8.5
    ) -> Dict[str, Any]:
        """
        Calculates Gross/Net profit, BEP, DSCR (Debt Service Coverage Ratio), ROI, and Payback period.
        """
        monthly_gross_profit = monthly_revenue - monthly_opex
        
        # 10% annual straight-line depreciation on CAPEX
        monthly_depreciation = (total_capex * 0.10) / 12.0
        
        # Monthly Net Profit (after OPEX, EMI loan repayment, and depreciation)
        monthly_net_profit = monthly_gross_profit - monthly_emi - monthly_depreciation
        
        # Annualized metrics
        annual_gross_cashflow = monthly_gross_profit * 12.0
        annual_net_profit = monthly_net_profit * 12.0
        annual_debt_service = monthly_emi * 12.0
        
        # Debt Service Coverage Ratio (DSCR = Net Operating Income / Total Debt Service)
        if annual_debt_service > 0:
            dscr_ratio = round(annual_gross_cashflow / annual_debt_service, 2)
        else:
            dscr_ratio = 9.99
            
        # Break-Even Point (in months)
        if monthly_gross_profit > 0:
            break_even_months = round(total_capex / monthly_gross_profit, 1)
        else:
            break_even_months = 99.0
            
        # Return on Investment (ROI)
        if total_project_cost > 0:
            roi_percentage = round((annual_net_profit / total_project_cost) * 100.0, 2)
        else:
            roi_percentage = 0.0
            
        # Payback period (Years)
        annual_cash_inflow = annual_net_profit + (monthly_depreciation * 12.0)
        if annual_cash_inflow > 0:
            payback_period_years = round(total_project_cost / annual_cash_inflow, 2)
        else:
            payback_period_years = 99.0

        is_bankable = dscr_ratio >= 1.4 and monthly_net_profit > 0

        return {
            "projected_monthly_revenue": round(monthly_revenue, 2),
            "monthly_gross_profit": round(monthly_gross_profit, 2),
            "monthly_net_profit": round(monthly_net_profit, 2),
            "break_even_months": break_even_months,
            "dscr_ratio": dscr_ratio,
            "is_bankable": is_bankable,
            "roi_percentage": roi_percentage,
            "payback_period_years": payback_period_years
        }

    @staticmethod
    def generate_5year_cashflow(
        total_project_cost: float,
        monthly_revenue: float,
        monthly_opex: float,
        monthly_emi: float,
        loan_tenure_months: int = 60
    ) -> Dict[str, Any]:
        """
        Generates 5-year cash flow projections with 5% annual revenue growth and 3% inflation on OPEX.
        """
        yearly_data = []
        cumulative_cashflow = -total_project_cost

        for year in range(1, 6):
            rev_growth = math.pow(1.05, year - 1)
            cost_inflation = math.pow(1.03, year - 1)
            
            annual_rev = monthly_revenue * 12.0 * rev_growth
            annual_opex = monthly_opex * 12.0 * cost_inflation
            annual_emi = monthly_emi * 12.0 if (year * 12) <= loan_tenure_months else 0.0
            
            annual_net_cash = annual_rev - annual_opex - annual_emi
            cumulative_cashflow += annual_net_cash
            
            yearly_data.append({
                "year": year,
                "revenue": round(annual_rev, 2),
                "opex": round(annual_opex, 2),
                "debt_service": round(annual_emi, 2),
                "net_cash_flow": round(annual_net_cash, 2),
                "cumulative_cash_flow": round(cumulative_cashflow, 2)
            })

        return {
            "projection_horizon_years": 5,
            "yearly_projections": yearly_data
        }

    @classmethod
    def compute_full_financial_plan(
        cls,
        capex: float,
        monthly_opex: float,
        monthly_revenue: float,
        working_capital_months: int = 3,
        user_margin_available: float = 50000.0,
        scheme_code: str = "PMEGP",
        category: SocialCategoryEnum = SocialCategoryEnum.GENERAL,
        is_rural: bool = True,
        loan_tenure_months: int = 60,
        annual_interest_rate: float = 8.5,
        has_seasonal_dip: bool = False
    ) -> FinancialBreakdownResponse:
        """
        Unified method that executes the complete financial model pipeline.
        """
        # Step 1: Project cost & working capital buffer
        cost_dict = cls.calculate_project_cost(
            capex=capex,
            monthly_opex=monthly_opex,
            working_capital_months=working_capital_months,
            has_seasonal_dip=has_seasonal_dip
        )
        total_cost = cost_dict["total_project_cost"]

        # Step 2: Capital structure (Margin, Subsidy, Loan)
        cap_dict = cls.calculate_capital_structure(
            total_project_cost=total_cost,
            user_margin_available=user_margin_available,
            scheme_code=scheme_code,
            category=category,
            is_rural=is_rural
        )

        # Step 3: Bank EMI
        emi = cls.calculate_emi(
            principal=cap_dict["net_bank_loan_required"],
            annual_rate=annual_interest_rate,
            tenure_months=loan_tenure_months
        )

        # Step 4: Profitability & Ratios (DSCR, BEP, ROI)
        prof_dict = cls.calculate_profitability_and_ratios(
            total_project_cost=total_cost,
            total_capex=capex,
            monthly_revenue=monthly_revenue,
            monthly_opex=monthly_opex,
            monthly_emi=emi,
            annual_rate=annual_interest_rate
        )

        # Step 5: 5-Year Cash Flows
        cash_flow = cls.generate_5year_cashflow(
            total_project_cost=total_cost,
            monthly_revenue=monthly_revenue,
            monthly_opex=monthly_opex,
            monthly_emi=emi,
            loan_tenure_months=loan_tenure_months
        )

        cost_breakdown = {
            "capex": cost_dict["total_capex"],
            "monthly_opex": cost_dict["total_opex_monthly"],
            "working_capital_months": cost_dict["effective_wc_months"],
            "working_capital_buffer": cost_dict["working_capital_buffer"],
            "total_project_cost": total_cost,
            "user_margin_amount": cap_dict["user_margin_amount"],
            "subsidy_amount": cap_dict["subsidy_amount_eligible"],
            "net_loan_amount": cap_dict["net_bank_loan_required"]
        }

        return FinancialBreakdownResponse(
            total_capex=cost_dict["total_capex"],
            total_opex_monthly=cost_dict["total_opex_monthly"],
            working_capital_buffer=cost_dict["working_capital_buffer"],
            total_project_cost=total_cost,
            user_margin_amount=cap_dict["user_margin_amount"],
            user_margin_pct=cap_dict["user_margin_pct"],
            subsidy_amount_eligible=cap_dict["subsidy_amount_eligible"],
            subsidy_pct=cap_dict["subsidy_pct"],
            matched_scheme_code=cap_dict["matched_scheme_code"],
            net_bank_loan_required=cap_dict["net_bank_loan_required"],
            loan_tenure_months=loan_tenure_months,
            annual_interest_rate=annual_interest_rate,
            monthly_emi_amount=emi,
            projected_monthly_revenue=prof_dict["projected_monthly_revenue"],
            monthly_gross_profit=prof_dict["monthly_gross_profit"],
            monthly_net_profit=prof_dict["monthly_net_profit"],
            break_even_months=prof_dict["break_even_months"],
            dscr_ratio=prof_dict["dscr_ratio"],
            is_bankable=prof_dict["is_bankable"],
            roi_percentage=prof_dict["roi_percentage"],
            payback_period_years=prof_dict["payback_period_years"],
            cash_flow_5yr=cash_flow,
            cost_breakdown=cost_breakdown
        )

