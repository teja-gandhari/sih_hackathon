from typing import Dict, Any, List, Tuple
from app.schemas.financial import FinancialBreakdownResponse
from app.schemas.feasibility import (
    FeasibilityBreakdownResponse,
    SWOTAnalysis,
    MarketReachAnalysis,
    OpportunityAnalysis,
    ThreatsIdentification,
    CompetitorMapping,
    ProductMarketValuePricing
)
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

        # Module 1 Sub-component 1: Market Reach
        consumer_base_est = int(max(5000, min(35000, market_data.get("district_population", 20000) * 0.12 or 14500)))
        dist_channels = [
            "Local village shandies/haats (weekly cash realization)",
            "Direct household delivery within 5-8km cluster",
            "Institutional aggregation via local SHG / Farmer Producer Organization (FPO)",
            "Wholesale mandi linkage in nearby sub-district hub"
        ]
        market_reach = MarketReachAnalysis(
            radius_km=7.5,
            estimated_consumer_base=consumer_base_est,
            primary_distribution_channels=dist_channels,
            rural_accessibility_summary=(
                f"Accessible consumer base of ~{consumer_base_est:,} individuals within a 5-10 km radius. "
                "Primary distribution balances weekly village markets and direct local retail."
            )
        )

        # Module 1 Sub-component 2: Opportunity Analysis
        underserved = [
            f"Hygienic, standardized {business_type.get('name_en', 'product')} supply for local retail",
            "Bulk supply to village tea stalls, hostels, and weekly catering functions",
            "Value addition into localized processed variants during peak festive seasons"
        ]
        opportunity_analysis = OpportunityAnalysis(
            underserved_niches=underserved,
            demand_supply_gap_description=(
                f"Current supply depends heavily on informal unorganized vendors. "
                f"A reliable, formalized micro-unit can capture 25-35% of the local block market share."
            ),
            recommended_value_addition="Introduce small branded packaging and doorstep subscription delivery."
        )

        # Module 1 Sub-component 4: Threats Identification
        threats_identification = ThreatsIdentification(
            supply_chain_bottlenecks=[
                "High seasonal input/fodder costs during pre-monsoon summer months",
                "Limited local cold chain storage leading to perishable distress sales"
            ],
            seasonal_demand_fluctuations=(
                "Cash flow surges post-harvest (Oct-Dec, Apr-May) and contracts in monsoon lean season."
            ),
            single_buyer_dependency_risk=(
                "Avoid selling 100% volume to a single middleman. Diversify across 3-4 local retail outlets."
            ),
            mitigation_strategies=[
                "Maintain a 4-5 month working capital reserve as structured in the financial model",
                "Form bulk procurement tie-ups with neighbouring farmers for raw material discounts"
            ]
        )

        # Module 1 Sub-component 5: Competitor Mapping
        block_density = round((formal_comp + informal_comp) / 2.5, 1)
        saturation_lvl = "low" if total_comp <= 3 else ("moderate" if total_comp <= 7 else "saturated")
        unserved_headroom = max(15.0, round(100.0 - (total_comp * 8.5), 1))

        competitor_mapping = CompetitorMapping(
            block_density_per_10k=block_density,
            formal_registered_competitors=formal_comp,
            estimated_informal_competitors=informal_comp,
            market_saturation_level=saturation_lvl,
            unserved_demand_headroom_pct=unserved_headroom
        )

        # Module 1 Sub-component 6: Product Market Value & Pricing
        product_market_value = ProductMarketValuePricing(
            suggested_price_point=round(ticket_size, 2),
            unit_label=business_type.get("unit_label", "Unit"),
            regional_purchasing_power_tier=pp_tier,
            mgnrega_daily_wage_benchmark=mgnrega_wage,
            affordability_tier_fit=pp_msg,
            optimal_pricing_strategy=(
                f"Competitive penetration pricing at ₹{ticket_size:.0f}/{business_type.get('unit_label', 'unit')}, "
                f"anchored within the rural wage ceiling (₹{mgnrega_wage:.0f}/day MGNREGA rate)."
            )
        )

        # Grounded SWOT Generation (Module 1 Sub-component 3)
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
            market_reach=market_reach,
            opportunity_analysis=opportunity_analysis,
            threats_identification=threats_identification,
            competitor_mapping=competitor_mapping,
            product_market_value=product_market_value,
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

    @classmethod
    async def analyze_unified_feasibility(
        cls,
        db: Any,
        request: Any,
        user_id: Optional[str] = None
    ) -> Any:
        """
        Unified Deterministic Feasibility Engine.
        Integrates:
        1. Financial Calculation Engine (40% weight)
        2. Hyper-Local Market Analysis Engine (40% weight)
        3. Scheme Eligibility & Structuring Engine (10% weight)
        4. Ground Risk & Saturation Factors (10% weight)
        """
        from app.schemas.feasibility import UnifiedFeasibilityAnalyzeResponse
        from app.schemas.market import MarketAnalysisRequest
        from app.services.financial_engine import FinancialCalculationEngine
        from app.services.scheme_engine import SchemeEligibilityEngine
        from app.services.market_analysis_engine import HyperLocalMarketAnalysisEngine
        from app.models.application import BusinessApplication, FinancialPlan, FeasibilityAssessment
        from app.models.business import BusinessType
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select

        app_id = request.application_id
        cat_key = (request.business_category or "dairy").strip().lower()
        margin_avail = float(request.available_margin_capital or 50000.0)
        soc_cat = request.category or "obc"
        is_rural = bool(request.is_rural if request.is_rural is not None else True)
        village_name = request.village or "Village A"
        district_name = request.district or "Nalgonda"
        state_name = request.state or "Telangana"
        radius_km = float(request.radius_km or 5.0)

        # ── 1. Financial Evaluation (40% Weight) ──────────────────────────────
        dscr = 2.5
        roi = 19.5
        break_even = 20.0
        total_project_cost = margin_avail / 0.10
        monthly_emi = 5200.0
        monthly_net_profit = 7800.0
        subsidy_amount = 0.0
        matched_scheme_code = "PMEGP"
        business_display_name = cat_key.capitalize()

        if app_id:
            res_app = await db.execute(
                select(BusinessApplication)
                .options(
                    selectinload(BusinessApplication.business_type),
                    selectinload(BusinessApplication.financial_plan)
                )
                .where(BusinessApplication.id == app_id)
            )
            app_obj = res_app.scalars().first()
            if app_obj:
                bt = app_obj.business_type
                if bt:
                    business_display_name = bt.name_en
                fp = app_obj.financial_plan
                if not fp:
                    scale = app_obj.scale_units / max(bt.default_scale, 1) if bt else 1.0
                    capex = (bt.default_capex if bt else 350000.0) * scale
                    opex = (bt.default_monthly_opex if bt else 25000.0) * scale
                    rev = (bt.default_monthly_revenue if bt else 38000.0) * scale
                    fin_plan_calc = FinancialCalculationEngine.compute_full_financial_plan(
                        capex=capex,
                        monthly_opex=opex,
                        monthly_revenue=rev,
                        user_margin_available=app_obj.user_margin_available,
                        category=soc_cat,
                        is_rural=is_rural
                    )
                    dscr = fin_plan_calc.dscr_ratio
                    roi = fin_plan_calc.roi_percentage
                    break_even = fin_plan_calc.break_even_months
                    total_project_cost = fin_plan_calc.total_project_cost
                    monthly_emi = fin_plan_calc.monthly_emi_amount
                    monthly_net_profit = fin_plan_calc.monthly_net_profit
                    matched_scheme_code = fin_plan_calc.matched_scheme_code
                    subsidy_amount = fin_plan_calc.subsidy_amount_eligible
                else:
                    dscr = fp.dscr_ratio
                    roi = fp.roi_percentage
                    break_even = fp.break_even_months
                    total_project_cost = fp.total_project_cost
                    monthly_emi = fp.monthly_emi_amount
                    monthly_net_profit = fp.monthly_net_profit
                    matched_scheme_code = fp.matched_scheme_code
                    subsidy_amount = fp.subsidy_amount_eligible
        else:
            # Calibrate financial ratios based on margin capital
            if total_project_cost > 5000000.0:  # Exceeds max concessional ceiling
                dscr = 0.9
                roi = 6.0
                break_even = 50.0
            elif total_project_cost <= 140000.0:
                dscr = 2.8
                roi = 24.0
                break_even = 14.0
            else:
                dscr = 2.4
                roi = 19.0
                break_even = 21.0

        # Financial Score Calculation (0-100)
        dscr_pts = 40.0 if dscr >= 2.0 else (34.0 if dscr >= 1.4 else (22.0 if dscr >= 1.1 else 8.0))
        roi_pts = 35.0 if roi >= 20.0 else (30.0 if roi >= 15.0 else (20.0 if roi >= 10.0 else 10.0))
        be_pts = 25.0 if break_even <= 14.0 else (20.0 if break_even <= 24.0 else (14.0 if break_even <= 36.0 else 6.0))
        financial_score = round(min(100.0, max(15.0, dscr_pts + roi_pts + be_pts)), 1)

        # ── 2. Scheme / Loan Suitability (10% Weight) ─────────────────────────
        schemes = SchemeEligibilityEngine.evaluate_eligibility(
            sector_code=cat_key,
            project_cost=total_project_cost,
            user_margin_available=margin_avail,
            category=soc_cat,
            is_rural=is_rural
        )
        eligible_schemes = [s for s in schemes if s.eligible]
        if eligible_schemes:
            top_scheme = eligible_schemes[0]
            if top_scheme.subsidy_percentage >= 25.0:
                scheme_score = 94.0
            elif top_scheme.subsidy_percentage >= 15.0:
                scheme_score = 86.0
            else:
                scheme_score = 80.0
            matched_scheme_name = top_scheme.scheme_name
        elif total_project_cost <= 5000000.0:
            scheme_score = 75.0
            matched_scheme_name = "State Channelizing Agency Term Loan Scheme"
        else:
            scheme_score = 30.0
            matched_scheme_name = "Standard Commercial Bank Loan (Ceiling Exceeded)"

        # ── 3. Hyper-Local Market Opportunity (40% Weight) ───────────────────
        mkt_req = MarketAnalysisRequest(
            village=village_name,
            block=request.block,
            district=district_name,
            state=state_name,
            business_category=cat_key,
            radius_km=radius_km,
            village_population=request.village_population
        )
        mkt_res = await HyperLocalMarketAnalysisEngine.analyze_market_viability(
            db=db,
            request=mkt_req,
            user_id=user_id
        )
        market_score = round(mkt_res.market_opportunity.score, 1)
        sat_pct = mkt_res.market_capacity_analysis.market_saturation_percentage
        comp_level = mkt_res.competition_analysis.competition_level
        capacity_gap = mkt_res.market_capacity_analysis.capacity_gap
        existing_comp = mkt_res.competition_analysis.existing_competitor_count
        reachable_pop = mkt_res.population_analysis.reachable_population or 5000

        # ── 4. Risk Factors & Saturation Penalties (10% Weight) ───────────────
        risk_base = 100.0
        if sat_pct >= 100.0:
            risk_base -= 28.0
        elif sat_pct >= 75.0:
            risk_base -= 16.0
        elif sat_pct >= 50.0:
            risk_base -= 6.0

        if existing_comp >= 5:
            risk_base -= 14.0
        elif existing_comp >= 3:
            risk_base -= 6.0

        if dscr < 1.4:
            risk_base -= 18.0

        risk_score = round(max(15.0, min(95.0, risk_base)), 1)

        # ── 5. Overall Deterministic Composite Score (0 to 100) ───────────────
        # Formula: 40% Financial + 40% Market + 10% Scheme + 10% Risk
        overall_feasibility_score = round(
            (0.40 * financial_score) +
            (0.40 * market_score) +
            (0.10 * scheme_score) +
            (0.10 * risk_score),
            1
        )
        overall_feasibility_score = max(5.0, min(99.0, overall_feasibility_score))

        # Classification
        if overall_feasibility_score >= 80.0:
            classification = "HIGHLY_FEASIBLE"
        elif overall_feasibility_score >= 65.0:
            classification = "FEASIBLE"
        elif overall_feasibility_score >= 50.0:
            classification = "MODERATE"
        else:
            classification = "HIGH_RISK"

        # ── 6. Deterministic SWOT & Explanation ───────────────────────────────
        strengths = [
            f"Strong debt service capacity with DSCR of {dscr:.2f} (Bank benchmark: >= 1.40).",
            f"Concessional credit and subsidy matching under {matched_scheme_name}.",
            f"Promoter margin contribution of ₹{margin_avail:,.0f} effectively unlocks 90% loan leverage."
        ]
        if financial_score >= 80.0:
            strengths.append(f"Healthy projected ROI of {roi:.1f}% with break-even within {break_even:.0f} months.")

        weaknesses = [
            "Sensitivity to seasonal cash flow cycles during pre-harvest lean months.",
            "Working capital buffer of at least 3-4 months OPEX is recommended."
        ]
        if dscr < 1.4:
            weaknesses.append("Debt service coverage is narrow; tight cash management required.")

        opportunities = [
            f"Reachable market population of {reachable_pop:,} within {radius_km} km radius.",
            f"Local market capacity supports approximately {mkt_res.market_capacity_analysis.estimated_market_capacity} operating units."
        ]
        if capacity_gap > 0:
            opportunities.append(f"Unserved capacity gap of ~{capacity_gap} businesses remaining in the local cluster.")

        key_risks = []
        if sat_pct >= 90.0:
            key_risks.append(f"Market is approaching saturation at {sat_pct:.0f}% of estimated capacity.")
        if existing_comp >= 4:
            key_risks.append(f"High local competitor concentration with {existing_comp} existing businesses nearby.")
        key_risks.append("Raw material price fluctuations and localized agricultural revenue swings.")

        explanation = (
            f"The proposed {business_display_name} in {village_name}, {district_name} achieves an overall Feasibility Score of "
            f"{overall_feasibility_score:.0f}/100 ({classification}). Financial viability scored {financial_score:.0f}/100 "
            f"(DSCR: {dscr:.2f}, ROI: {roi:.1f}%), hyper-local market opportunity scored {market_score:.0f}/100 "
            f"(Capacity: {mkt_res.market_capacity_analysis.estimated_market_capacity} units, Saturation: {sat_pct:.0f}%), "
            f"government scheme suitability scored {scheme_score:.0f}/100 ({matched_scheme_name}), and risk stability scored {risk_score:.0f}/100."
        )

        # ── 7. Store / Update FeasibilityAssessment in PostgreSQL ─────────────
        if app_id:
            try:
                res_fa = await db.execute(select(FeasibilityAssessment).where(FeasibilityAssessment.application_id == app_id))
                fa_db = res_fa.scalars().first()
                if not fa_db:
                    fa_db = FeasibilityAssessment(application_id=app_id)
                    db.add(fa_db)

                fa_db.overall_score = overall_feasibility_score
                fa_db.market_demand_score = market_score
                fa_db.financial_viability_score = financial_score
                fa_db.risk_score = risk_score
                fa_db.viability_rating = classification.lower()
                fa_db.swot_analysis = {
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "opportunities": opportunities,
                    "threats": key_risks
                }
                fa_db.key_recommendations = [explanation]
                await db.commit()
            except Exception:
                pass

        return UnifiedFeasibilityAnalyzeResponse(
            overall_feasibility_score=overall_feasibility_score,
            classification=classification,
            financial_score=financial_score,
            market_score=market_score,
            scheme_score=scheme_score,
            risk_score=risk_score,
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            key_risks=key_risks,
            deterministic_explanation=explanation,
            financial_summary={
                "total_project_cost": total_project_cost,
                "user_margin_available": margin_avail,
                "dscr_ratio": dscr,
                "roi_percentage": roi,
                "break_even_months": break_even,
                "monthly_net_profit": monthly_net_profit,
                "monthly_emi": monthly_emi
            },
            market_summary={
                "village_population": reachable_pop,
                "existing_competitors": existing_comp,
                "estimated_market_capacity": mkt_res.market_capacity_analysis.estimated_market_capacity,
                "market_saturation_percentage": sat_pct,
                "competition_level": comp_level
            },
            scheme_summary={
                "matched_scheme_code": matched_scheme_code,
                "matched_scheme_name": matched_scheme_name,
                "eligible_subsidy_amount": subsidy_amount
            }
        )


