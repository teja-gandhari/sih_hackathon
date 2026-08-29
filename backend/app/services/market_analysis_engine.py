from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.market import BusinessCategoryBenchmark, MarketAnalysisRecord
from app.schemas.market import (
    MarketAnalysisRequest,
    MarketAnalysisResponse,
    LocationDetails,
    LocationCoordinates,
    PopulationAnalysisResult,
    CompetitionAnalysisResult,
    MarketCapacityAnalysisResult,
    MarketOpportunityResult,
    MarketRecommendationResult,
    DataQualityResult
)
from app.services.population_service import PopulationService
from app.services.osm_service import OpenStreetMapService


class HyperLocalMarketAnalysisEngine:
    """
    Deterministic Hyper-Local Market Demand, Competition & Viability Engine.
    
    Answers the core user question:
    'Can my local population and market support one more business of this type?'
    
    Zero AI hallucination for math — completely grounded in deterministic demographic equations.
    """

    # Configurable Default Category Benchmarks
    DEFAULT_CATEGORY_BENCHMARKS = {
        "kirana": {
            "name": "Kirana & Grocery Store",
            "min_pop": 600.0,
            "ideal_pop": 1000.0,
            "competition_weight": 0.35,
            "demand_weight": 0.35,
            "reach_weight": 0.20,
            "market_reach_weight": 0.10,
            "default_radius_km": 5.0
        },
        "dairy": {
            "name": "Dairy & Milk Enterprise",
            "min_pop": 500.0,
            "ideal_pop": 800.0,
            "competition_weight": 0.35,
            "demand_weight": 0.35,
            "reach_weight": 0.20,
            "market_reach_weight": 0.10,
            "default_radius_km": 5.0
        },
        "food_processing": {
            "name": "Food Processing & Agri Mill",
            "min_pop": 1500.0,
            "ideal_pop": 2500.0,
            "competition_weight": 0.35,
            "demand_weight": 0.35,
            "reach_weight": 0.20,
            "market_reach_weight": 0.10,
            "default_radius_km": 8.0
        },
        "food": {
            "name": "Restaurant & Tiffin Center",
            "min_pop": 1200.0,
            "ideal_pop": 2000.0,
            "competition_weight": 0.35,
            "demand_weight": 0.35,
            "reach_weight": 0.20,
            "market_reach_weight": 0.10,
            "default_radius_km": 5.0
        },
        "retail": {
            "name": "Rural Retail & Variety Store",
            "min_pop": 800.0,
            "ideal_pop": 1500.0,
            "competition_weight": 0.35,
            "demand_weight": 0.35,
            "reach_weight": 0.20,
            "market_reach_weight": 0.10,
            "default_radius_km": 5.0
        },
        "agriculture": {
            "name": "Agro-Inputs & Seed Store",
            "min_pop": 1000.0,
            "ideal_pop": 2000.0,
            "competition_weight": 0.35,
            "demand_weight": 0.35,
            "reach_weight": 0.20,
            "market_reach_weight": 0.10,
            "default_radius_km": 8.0
        },
        "textiles": {
            "name": "Textiles & Garment Stitching",
            "min_pop": 1500.0,
            "ideal_pop": 3000.0,
            "competition_weight": 0.35,
            "demand_weight": 0.35,
            "reach_weight": 0.20,
            "market_reach_weight": 0.10,
            "default_radius_km": 6.0
        },
        "handicrafts": {
            "name": "Handicrafts & Rural Artisans",
            "min_pop": 2000.0,
            "ideal_pop": 4000.0,
            "competition_weight": 0.35,
            "demand_weight": 0.35,
            "reach_weight": 0.20,
            "market_reach_weight": 0.10,
            "default_radius_km": 10.0
        },
        "services": {
            "name": "Rural Technical & Repair Services",
            "min_pop": 1000.0,
            "ideal_pop": 2000.0,
            "competition_weight": 0.35,
            "demand_weight": 0.35,
            "reach_weight": 0.20,
            "market_reach_weight": 0.10,
            "default_radius_km": 5.0
        }
    }

    @classmethod
    async def analyze_market_viability(
        cls,
        db: AsyncSession,
        request: MarketAnalysisRequest,
        user_id: Optional[str] = None
    ) -> MarketAnalysisResponse:
        """
        Main analysis pipeline implementing population provider, competitor finder,
        capacity analysis, saturation scoring, and opportunity classification.
        """
        cat_key = (request.business_category or "kirana").strip().lower()
        village_name = request.village or "Village A"
        district_name = request.district or "Nalgonda"
        state_name = request.state or "Telangana"
        radius_km = float(request.radius_km or 5.0)

        # 1. Fetch Configurable Benchmark from Database or Fallback Defaults
        b_query = select(BusinessCategoryBenchmark).where(BusinessCategoryBenchmark.category_code == cat_key)
        b_res = await db.execute(b_query)
        db_benchmark = b_res.scalars().first()

        if db_benchmark:
            category_display_name = db_benchmark.category_name
            ideal_pop_per_biz = float(db_benchmark.ideal_population_per_business or 1000.0)
            min_pop_per_biz = float(db_benchmark.minimum_population_per_business or 600.0)
            w_comp = float(db_benchmark.competition_weight or 0.35)
            w_demand = float(db_benchmark.demand_weight or 0.35)
            w_reach = float(db_benchmark.reach_weight or 0.20)
            w_loc = float(db_benchmark.market_reach_weight or 0.10)
        else:
            default_bm = cls.DEFAULT_CATEGORY_BENCHMARKS.get(cat_key, cls.DEFAULT_CATEGORY_BENCHMARKS["kirana"])
            category_display_name = default_bm["name"]
            ideal_pop_per_biz = default_bm["ideal_pop"]
            min_pop_per_biz = default_bm["min_pop"]
            w_comp = default_bm["competition_weight"]
            w_demand = default_bm["demand_weight"]
            w_reach = default_bm["reach_weight"]
            w_loc = default_bm["market_reach_weight"]

        # 2. Retrieve Population Data
        pop_data = await PopulationService.get_population_data(
            db=db,
            village=village_name,
            district=district_name,
            block=request.block,
            state=state_name,
            radius_km=radius_km,
            user_override_pop=request.village_population
        )

        village_pop = pop_data["village_population"]
        reachable_pop = pop_data["reachable_population"]
        lat = pop_data["latitude"]
        lon = pop_data["longitude"]
        pop_source = pop_data["source"]
        is_pop_estimated = pop_data["is_estimated"]
        pop_retrieved_at = pop_data["retrieved_at"]

        # 3. Retrieve Competitor Data
        comp_count, comp_names, comp_source = await OpenStreetMapService.get_competitors(
            db=db,
            business_category=cat_key,
            latitude=lat,
            longitude=lon,
            radius_km=radius_km,
            village_name=village_name
        )

        # 4. Core Deterministic Market Calculations
        # 4.1 Population Per Existing Competitor
        if comp_count > 0:
            pop_per_existing_competitor = round(reachable_pop / comp_count, 1)
        else:
            pop_per_existing_competitor = float(reachable_pop)

        # 4.2 Projected Population Per Business (+1 for proposed new unit)
        projected_pop_per_biz = round(reachable_pop / (comp_count + 1), 1)

        # 4.3 Estimated Market Capacity
        estimated_market_capacity = int(round(reachable_pop / ideal_pop_per_biz))
        if estimated_market_capacity < 1 and reachable_pop >= (min_pop_per_biz * 0.5):
            estimated_market_capacity = 1

        # 4.4 Capacity Gap (Room for new businesses)
        capacity_gap = estimated_market_capacity - comp_count

        # 4.5 Market Saturation Percentage
        if estimated_market_capacity > 0:
            saturation_pct = round((comp_count / estimated_market_capacity) * 100.0, 1)
        else:
            saturation_pct = 150.0 if comp_count > 0 else 0.0

        # 5. Market Opportunity Scoring (0 to 100)
        # Factor A: Demand Capacity Score (Weight: 35%)
        if estimated_market_capacity <= 0:
            demand_capacity_score = 15.0
        elif capacity_gap >= 3:
            demand_capacity_score = 95.0
        elif capacity_gap == 2:
            demand_capacity_score = 85.0
        elif capacity_gap == 1:
            demand_capacity_score = 72.0
        elif capacity_gap == 0:
            # Saturated (capacity met)
            demand_capacity_score = 42.0
        elif capacity_gap == -1:
            demand_capacity_score = 25.0
        else:
            # Heavily over-saturated
            demand_capacity_score = 10.0

        # Factor B: Competition Gap Score (Weight: 35%)
        if comp_count == 0:
            competition_gap_score = 98.0  # Strong unmet-demand signal
        else:
            ratio = projected_pop_per_biz / ideal_pop_per_biz
            if ratio >= 1.5:
                competition_gap_score = 95.0
            elif ratio >= 1.0:
                competition_gap_score = 82.0
            elif ratio >= 0.8:
                competition_gap_score = 60.0
            elif ratio >= 0.6:
                competition_gap_score = 40.0
            else:
                competition_gap_score = 15.0

        # Factor C: Reachable Population Score (Weight: 20%)
        pop_threshold_ratio = reachable_pop / (min_pop_per_biz * 2.0)
        reachable_population_score = round(min(100.0, max(10.0, pop_threshold_ratio * 100.0)), 1)

        # Factor D: Location / Market Reach Score (Weight: 10%)
        market_reach_score = 85.0 if radius_km <= 5.0 else 75.0

        # Total Weighted Opportunity Score
        market_opportunity_score = round(
            (w_demand * demand_capacity_score) +
            (w_comp * competition_gap_score) +
            (w_reach * reachable_population_score) +
            (w_loc * market_reach_score),
            1
        )
        market_opportunity_score = max(5.0, min(99.0, market_opportunity_score))

        # 6. Classifications
        # Opportunity Classification
        if market_opportunity_score >= 80.0:
            classification = "HIGH_OPPORTUNITY"
        elif market_opportunity_score >= 60.0:
            classification = "MODERATE_OPPORTUNITY"
        elif market_opportunity_score >= 40.0:
            classification = "LOW_OPPORTUNITY"
        else:
            classification = "HIGH_SATURATION_HIGH_RISK"

        # Competition Classification
        if saturation_pct >= 90.0 or (projected_pop_per_biz < min_pop_per_biz and comp_count >= 2):
            competition_level = "HIGH"
        elif saturation_pct >= 55.0 or comp_count >= 2:
            competition_level = "MODERATE"
        else:
            competition_level = "LOW"

        # 7. Generate Explainable Reasoning & Summary
        key_reasons = []
        if comp_count == 0:
            summary = (
                f"Currently there are 0 registered competitors in the {category_display_name} category serving a "
                f"reachable population of around {reachable_pop:,}. Your proposed enterprise will capture strong first-mover "
                f"advantage with an estimated market capacity for {estimated_market_capacity} businesses."
            )
            key_reasons.append("Zero registered competitors detected within the target radius (Unserved Market Potential)")
            key_reasons.append(f"Reachable population of {reachable_pop:,} easily sustains an initial micro-enterprise")
            should_proceed = True
            rec_level = "PROCEED"
        elif capacity_gap > 0 and projected_pop_per_biz >= min_pop_per_biz:
            summary = (
                f"There are approximately {comp_count} existing {category_display_name} businesses serving a population "
                f"of around {reachable_pop:,}. After your proposed business enters the market, the estimated population per "
                f"business would be approximately {projected_pop_per_biz:,.0f}. Based on the configured local market benchmark "
                f"({ideal_pop_per_biz:,.0f} people per business), there is healthy unserved market capacity (room for ~{capacity_gap} more units)."
            )
            key_reasons.append(f"Market capacity gap of ~{capacity_gap} businesses remaining in the local cluster")
            key_reasons.append(f"Projected population per business ({projected_pop_per_biz:,.0f}) exceeds minimum requirement ({min_pop_per_biz:,.0f})")
            should_proceed = True
            rec_level = "PROCEED" if market_opportunity_score >= 80.0 else "REVIEW"
        else:
            summary = (
                f"There are approximately {comp_count} existing {category_display_name} businesses serving a population "
                f"of around {reachable_pop:,}. After your proposed shop enters the market, the estimated population per "
                f"business would decrease to approximately {projected_pop_per_biz:,.0f}. Based on the configured local "
                f"market benchmark ({ideal_pop_per_biz:,.0f} people per business), the market is approaching saturation."
            )
            key_reasons.append(f"Projected population per business ({projected_pop_per_biz:,.0f}) drops near or below the benchmark threshold ({ideal_pop_per_biz:,.0f})")
            key_reasons.append(f"Market saturation is high at {saturation_pct:.0f}% of estimated capacity")
            if comp_count >= 5:
                key_reasons.append("High existing competitor concentration in immediate village center")
            should_proceed = False
            rec_level = "REVIEW" if market_opportunity_score >= 40.0 else "HIGH_RISK"

        # 8. Data Quality & Limitations
        sources = [pop_source, comp_source]
        limitations = []
        if is_pop_estimated:
            limitations.append("Village population is estimated using regional Gram Panchayat census proxy.")
            confidence = "MEDIUM"
        else:
            confidence = "HIGH"

        if "Overpass" not in comp_source:
            limitations.append("Competitor density calibrated via ground MSME directory benchmarks; unorganized street vendors may vary.")

        # 9. Build Response Object
        response = MarketAnalysisResponse(
            location=LocationDetails(
                village=village_name,
                block=request.block,
                district=district_name,
                state=state_name,
                coordinates=LocationCoordinates(latitude=lat, longitude=lon)
            ),
            business_category=cat_key,
            analysis_radius_km=radius_km,
            population_analysis=PopulationAnalysisResult(
                village_population=village_pop,
                reachable_population=reachable_pop,
                population_source=pop_source,
                is_estimated=is_pop_estimated,
                retrieved_at=pop_retrieved_at
            ),
            competition_analysis=CompetitionAnalysisResult(
                existing_competitor_count=comp_count,
                competitor_names=comp_names,
                competition_level=competition_level,
                competitor_source=comp_source,
                population_per_existing_competitor=pop_per_existing_competitor,
                projected_population_per_business=projected_pop_per_biz
            ),
            market_capacity_analysis=MarketCapacityAnalysisResult(
                recommended_population_per_business=ideal_pop_per_biz,
                estimated_market_capacity=estimated_market_capacity,
                existing_businesses=comp_count,
                capacity_gap=capacity_gap,
                market_saturation_percentage=saturation_pct
            ),
            market_opportunity=MarketOpportunityResult(
                score=market_opportunity_score,
                classification=classification,
                demand_capacity_score=demand_capacity_score,
                competition_gap_score=competition_gap_score,
                reachable_population_score=reachable_population_score,
                market_reach_score=market_reach_score,
                reasoning=key_reasons
            ),
            recommendation=MarketRecommendationResult(
                should_proceed=should_proceed,
                recommendation_level=rec_level,
                summary=summary,
                key_reasons=key_reasons
            ),
            data_quality=DataQualityResult(
                confidence=confidence,
                sources=sources,
                limitations=limitations
            )
        )

        # 10. Persist Record to Database
        try:
            analysis_record = MarketAnalysisRecord(
                user_id=user_id,
                village_name=village_name,
                district_name=district_name,
                business_category=cat_key,
                radius_km=radius_km,
                market_opportunity_score=market_opportunity_score,
                market_potential=classification,
                market_saturation_percentage=saturation_pct,
                recommendation_level=rec_level,
                full_analysis_json=response.model_dump(mode="json")
            )
            db.add(analysis_record)
            await db.commit()
        except Exception as e:
            # Do not fail analysis request if record storage has issue
            pass

        return response

