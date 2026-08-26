from typing import Dict, Any, List, Tuple
from app.schemas.financial import FinancialBreakdownResponse
from app.schemas.feasibility import FeasibilityBreakdownResponse, SWOTAnalysis
from app.schemas.scheme import MatchedSchemeResult


class FeasibilityScoringEngine:
    """
    Advanced Rural Feasibility & Viability Engine.
    Incorporates Purchasing Power Fit, "Unserved vs. Unviable" Risk Classifier,
    Informal Sector Multipliers, and Regional Cluster Signals.
    """

    @staticmethod
    def calculate_purchasing_power_fit(
        typical_ticket_size: float,
        mgnrega_daily_wage: float,
        household_income: float,
        purchasing_power_tier: str,
        requires_daily_footfall: bool = False,
        is_export_or_wholesale: bool = False
    ) -> Tuple[float, str]:
        """
        Evaluates whether local disposable income can sustain the target product price point.
        """
        if is_export_or_wholesale:
            return 90.0, "Wholesale/Cooperative market model decouples retail local income constraints."

        affordability_ratio = typical_ticket_size / max(mgnrega_daily_wage, 100.0)

        tier_weights = {
            "low": 0.6,
            "lower_middle": 0.8,
            "middle": 1.0,
            "high": 1.2
        }
        tier_multiplier = tier_weights.get(purchasing_power_tier.lower(), 0.8)

        if affordability_ratio <= 0.20:
            score = 95.0 * tier_multiplier
            msg = "High affordability: Everyday essential price point matches local rural income."
        elif affordability_ratio <= 0.50:
            score = 78.0 * tier_multiplier
            msg = "Moderate affordability: Suitable for standard household purchase frequency."
        elif affordability_ratio <= 1.0:
            score = 52.0 * tier_multiplier
            msg = "Marginal affordability: Discretionary purchase dependent on harvest liquidity or festival seasons."
        else:
            score = 28.0 * tier_multiplier
            msg = "Severe affordability gap: Ticket price exceeds daily wage threshold; unviable for non-commute village."

        if requires_daily_footfall and purchasing_power_tier in ["low", "lower_middle"]:
            score *= 0.80

        score = max(5.0, min(100.0, score))
        return round(score, 1), msg

    @staticmethod
    def classify_market_gap(
        formal_competitors: int,
        informal_competitors: int,
        purchasing_power_score: float,
        demand_index: float,
        cluster_failure_rate: float
    ) -> Tuple[str, str, str, str]:
        """
        Distinguishes genuine market opportunities from deceptive zero-competitor traps.
        Returns: (classification, informal_warning, seasonal_warning, cluster_signal)
        """
        total_effective_competitors = formal_competitors + (1.5 * informal_competitors)

        # Classification logic
        if purchasing_power_score < 45.0:
            classification = "unviable_purchasing_power_gap"
            gap_explanation = (
                "Low competition detected, but average local purchasing power is below the price point "
                "typically needed to sustain this business — proceed with extreme caution."
            )
        elif total_effective_competitors <= 3.0 and demand_index >= 7.0 and purchasing_power_score >= 65.0:
            classification = "viable_and_unserved"
            gap_explanation = "Genuine high-potential market gap with strong purchasing power and low saturation."
        elif informal_competitors >= 4 and formal_competitors <= 1:
            classification = "saturated_informal_market"
            gap_explanation = (
                "Official MSME registries show low competition, but active unorganized/roadside vendors "
                "already capture majority of the local daily footfall."
            )
        else:
            classification = "niche_weekly_market"
            gap_explanation = "Viable primarily during weekly village shandies/haats or selective direct orders."

        # Warnings
        informal_warning = (
            f"Cross-check: {formal_competitors} formal units vs ~{informal_competitors} informal/unregistered "
            f"local vendors. Official registry data undercounts street/cart competition."
        )

        seasonal_warning = (
            "Agri-cyclical revenue concentration: Cash flow surges during Kharif/Rabi harvest (Oct-Dec, Apr-May) "
            "and contracts during lean monsoon/summer months. An extended 4-5 month working capital buffer is recommended."
        )

        cluster_signal = (
            f"Regional Cluster Benchmark: Similar enterprises within 25km show a {cluster_failure_rate:.1f}% "
            f"historical 1-year closure rate. Operating profitability requires strict cost control."
        )

        return classification, informal_warning, seasonal_warning, cluster_signal

    @classmethod
    def evaluate_feasibility(
        cls,
        application_id: str,
        financials: FinancialBreakdownResponse,
        matched_schemes: List[MatchedSchemeResult],
        market_data: Dict[str, Any],
        business_type: Dict[str, Any]
    ) -> FeasibilityBreakdownResponse:
        """
        Executes multi-factor composite feasibility scoring and risk classification.
        """
        ticket_size = business_type.get("typical_ticket_size", 50.0)
        is_export = business_type.get("is_export_or_wholesale", False)
        requires_footfall = business_type.get("requires_daily_footfall", False)

        mgnrega_wage = market_data.get("mgnrega_daily_wage_rate", 300.0)
        hh_income = market_data.get("average_monthly_household_income", 14000.0)
        pp_tier = market_data.get("purchasing_power_tier", "lower_middle")
        demand_index = market_data.get("demand_index", 7.5)
        formal_comp = market_data.get("formal_competitor_count", 2)
        informal_comp = market_data.get("estimated_informal_competitor_count", 4)
        cluster_failure_rate = market_data.get("regional_cluster_failure_rate_pct", 15.0)
        raw_mat_score = market_data.get("raw_material_availability_score", 8.0)
        infra_score = market_data.get("infrastructure_score", 7.0)

        # 1. Purchasing Power Fit (0 - 100)
        pp_score, pp_msg = cls.calculate_purchasing_power_fit(
            typical_ticket_size=ticket_size,
            mgnrega_daily_wage=mgnrega_wage,
            household_income=hh_income,
            purchasing_power_tier=pp_tier,
            requires_daily_footfall=requires_footfall,
            is_export_or_wholesale=is_export
        )

        # 2. Financial Viability Score (0 - 100)
        dscr = financials.dscr_ratio
        if dscr >= 2.0:
            fin_score = 95.0
        elif dscr >= 1.5:
            fin_score = 80.0
        elif dscr >= 1.2:
            fin_score = 60.0
        elif dscr >= 1.0:
            fin_score = 40.0
        else:
            fin_score = 20.0

        if financials.monthly_net_profit <= 0:
            fin_score = min(fin_score, 25.0)

        # 3. Market Demand Score (0 - 100)
        total_comp = formal_comp + (informal_comp * 0.8)
        market_demand_score = max(20.0, min(100.0, (demand_index * 10.0) - (total_comp * 3.5)))

        # 4. Resource Readiness Score (0 - 100)
        resource_score = ((raw_mat_score * 10.0) + (infra_score * 10.0)) / 2.0

        # 5. Risk Score (0 - 100)
        risk_factors = 0.0
        if dscr < 1.5:
            risk_factors += 30.0
        if pp_score < 50.0:
            risk_factors += 35.0
        if cluster_failure_rate > 20.0:
            risk_factors += 20.0
        if informal_comp >= 5:
            risk_factors += 15.0
        risk_score = min(100.0, max(10.0, risk_factors + 10.0))

        # 6. Composite Overall Feasibility Score (0 - 100)
        overall_score = (
            (0.30 * fin_score) +
            (0.25 * pp_score) +
            (0.20 * market_demand_score) +
            (0.15 * (100.0 - cluster_failure_rate * 2.0)) +
            (0.10 * resource_score)
        )
        overall_score = round(max(10.0, min(98.0, overall_score)), 1)

        # Viability Rating
        if overall_score >= 75.0:
            viability_rating = "high_feasibility"
        elif overall_score >= 58.0:
            viability_rating = "moderate_feasibility"
        elif overall_score >= 42.0:
            viability_rating = "high_risk"
        else:
            viability_rating = "not_recommended"

        # Market Gap Classification
        classification, informal_warn, seasonal_warn, cluster_sig = cls.classify_market_gap(
            formal_competitors=formal_comp,
            informal_competitors=informal_comp,
            purchasing_power_score=pp_score,
            demand_index=demand_index,
            cluster_failure_rate=cluster_failure_rate
        )

        # Grounded SWOT Generation
        swot = cls._generate_grounded_swot(
            business_name=business_type.get("name_en", "Micro Enterprise"),
            fin_score=fin_score,
            pp_score=pp_score,
            dscr=dscr,
            top_scheme=matched_schemes[0] if matched_schemes else None,
            classification=classification,
            informal_comp=informal_comp
        )

        # Recommendations
        recommendations = [
            f"Apply under {matched_schemes[0].scheme_name if matched_schemes else 'PMEGP'} for up to ₹{financials.subsidy_amount_eligible:,.0f} in capital subsidy.",
            f"Maintain an emergency buffer of at least 4 months OPEX (₹{financials.working_capital_buffer:,.0f}) to withstand seasonal lean periods.",
            "Establish direct forward linkages with nearby mandis or cooperatives to reduce retail price risk.",
            "Utilize digital UPI/QR payments and micro-accounting to maintain bank-ready repayment records."
        ]

        return FeasibilityBreakdownResponse(
            application_id=application_id,
            overall_score=overall_score,
            market_demand_score=round(market_demand_score, 1),
            financial_viability_score=round(fin_score, 1),
            purchasing_power_fit_score=pp_score,
            resource_readiness_score=round(resource_score, 1),
            risk_score=round(risk_score, 1),
            viability_rating=viability_rating,
            market_gap_classification=classification,
            informal_competition_warning=informal_warn,
            seasonal_cashflow_warning=seasonal_warn,
            regional_cluster_signal=cluster_sig,
            data_confidence_level=market_data.get("data_confidence_level", "moderate_proxy"),
            matched_schemes=matched_schemes,
            financial_summary=financials,
            swot_analysis=swot,
            key_recommendations=recommendations
        )

    @staticmethod
    def _generate_grounded_swot(
        business_name: str,
        fin_score: float,
        pp_score: float,
        dscr: float,
        top_scheme: Any,
        classification: str,
        informal_comp: int
    ) -> SWOTAnalysis:
        strengths = [
            f"Strong debt service capacity with DSCR of {dscr:.2f} (Bank benchmark: >= 1.40).",
            f"High concessional subsidy eligibility under {top_scheme.scheme_code if top_scheme else 'Govt Scheme'}.",
            "Low initial own-equity requirement (5%-10% margin money)."
        ]
        
        weaknesses = [
            "Sensitivity to seasonal cash flow cycles during pre-harvest months.",
            "Reliance on local infrastructure and cold chain/storage access."
        ]
        
        opportunities = [
            "Value addition and direct-to-consumer delivery in nearby semi-urban hubs.",
            "Aggregation through local SHGs / Farmer Producer Organizations (FPOs)."
        ]
        
        threats = [
            f"Competition from {informal_comp} informal local vendors offering unorganized credit.",
            "Raw material price volatility and climate-related supply shocks."
        ]

        if pp_score < 50.0:
            weaknesses.append("Local purchasing power is constrained relative to standard product ticket size.")

        return SWOTAnalysis(
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            threats=threats
        )

