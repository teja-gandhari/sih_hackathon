from typing import List, Dict, Any
from app.models.user import SocialCategoryEnum
from app.schemas.scheme import MatchedSchemeResult, SchemeMatchRequest


class SchemeEligibilityEngine:
    """
    Deterministic Government Scheme Matcher.
    Evaluates PMEGP, MUDRA (Shishu/Kishore/Tarun), PMFME, Stand-Up India, and NABARD.
    """

    SCHEMES_DATABASE = [
        {
            "scheme_code": "PMEGP",
            "scheme_name": "Prime Minister's Employment Generation Programme (PMEGP)",
            "nodal_agency": "KVIC / Ministry of MSME",
            "min_cost": 25000.0,
            "max_cost": 5000000.0,  # ₹50L manufacturing, ₹20L service
            "eligible_sectors": ["dairy", "agriculture", "food_processing", "retail", "textiles", "handicrafts", "services"],
            "eligible_categories": ["general", "obc", "sc", "st", "minority", "women_entrepreneur"],
            "min_age": 18,
            "general_rural_subsidy": 25.0,
            "general_urban_subsidy": 15.0,
            "special_rural_subsidy": 35.0,
            "special_urban_subsidy": 25.0,
            "max_subsidy_cap": 1250000.0,
            "general_margin_pct": 10.0,
            "special_margin_pct": 5.0,
            "interest_rate": 8.5,
            "benefits": [
                "Up to 35% capital subsidy for rural SC/ST/Women/OBC/Minority entrepreneurs",
                "Own contribution is only 5% for special categories, 10% for general",
                "Bank loan covers balance project cost after margin and subsidy"
            ]
        },
        {
            "scheme_code": "PMFME",
            "scheme_name": "PM Formalisation of Micro Food Processing Enterprises (PMFME)",
            "nodal_agency": "Ministry of Food Processing Industries (MoFPI)",
            "min_cost": 50000.0,
            "max_cost": 3000000.0,
            "eligible_sectors": ["food_processing", "agriculture", "dairy"],
            "eligible_categories": ["general", "obc", "sc", "st", "minority", "women_entrepreneur"],
            "min_age": 18,
            "general_rural_subsidy": 35.0,
            "general_urban_subsidy": 35.0,
            "special_rural_subsidy": 35.0,
            "special_urban_subsidy": 35.0,
            "max_subsidy_cap": 1000000.0,
            "general_margin_pct": 10.0,
            "special_margin_pct": 10.0,
            "interest_rate": 8.0,
            "benefits": [
                "35% credit-linked capital subsidy up to ₹10 Lakhs",
                "Specialized for agro-processing, spice grinding, flour/oil mills, dairy products",
                "Handholding support for FSSAI registration, branding, and packaging"
            ]
        },
        {
            "scheme_code": "MUDRA_KISHORE",
            "scheme_name": "Pradhan Mantri MUDRA Yojana (Kishore: ₹50k to ₹5 Lakhs)",
            "nodal_agency": "MUDRA / Department of Financial Services",
            "min_cost": 50000.0,
            "max_cost": 500000.0,
            "eligible_sectors": ["dairy", "retail", "agriculture", "food_processing", "textiles", "handicrafts", "services"],
            "eligible_categories": ["general", "obc", "sc", "st", "minority", "women_entrepreneur"],
            "min_age": 18,
            "general_rural_subsidy": 0.0,
            "general_urban_subsidy": 0.0,
            "special_rural_subsidy": 0.0,
            "special_urban_subsidy": 0.0,
            "max_subsidy_cap": 0.0,
            "general_margin_pct": 10.0,
            "special_margin_pct": 5.0,
            "interest_rate": 8.5,
            "benefits": [
                "Zero collateral required for loans up to ₹5 Lakhs",
                "No processing charges for micro enterprises",
                "Fast-track sanction via public sector & rural regional banks"
            ]
        },
        {
            "scheme_code": "MUDRA_TARUN",
            "scheme_name": "Pradhan Mantri MUDRA Yojana (Tarun: ₹5 Lakhs to ₹10 Lakhs)",
            "nodal_agency": "MUDRA / Department of Financial Services",
            "min_cost": 500000.0,
            "max_cost": 1000000.0,
            "eligible_sectors": ["dairy", "retail", "agriculture", "food_processing", "textiles", "handicrafts", "services"],
            "eligible_categories": ["general", "obc", "sc", "st", "minority", "women_entrepreneur"],
            "min_age": 18,
            "general_rural_subsidy": 0.0,
            "general_urban_subsidy": 0.0,
            "special_rural_subsidy": 0.0,
            "special_urban_subsidy": 0.0,
            "max_subsidy_cap": 0.0,
            "general_margin_pct": 15.0,
            "special_margin_pct": 10.0,
            "interest_rate": 9.0,
            "benefits": [
                "Collateral-free credit expansion up to ₹10 Lakhs",
                "Suitable for machinery upgrade and scaling established units"
            ]
        },
        {
            "scheme_code": "STANDUP_INDIA",
            "scheme_name": "Stand-Up India Scheme for Women & SC/ST Entrepreneurs",
            "nodal_agency": "SIDBI / Ministry of Finance",
            "min_cost": 1000000.0,
            "max_cost": 10000000.0,
            "eligible_sectors": ["dairy", "agriculture", "food_processing", "retail", "textiles", "handicrafts", "services"],
            "eligible_categories": ["sc", "st", "women_entrepreneur"],
            "min_age": 18,
            "general_rural_subsidy": 15.0,
            "general_urban_subsidy": 15.0,
            "special_rural_subsidy": 15.0,
            "special_urban_subsidy": 15.0,
            "max_subsidy_cap": 1500000.0,
            "general_margin_pct": 15.0,
            "special_margin_pct": 10.0,
            "interest_rate": 8.0,
            "benefits": [
                "Dedicated composite loan from ₹10 Lakhs to ₹1 Crore for SC/ST and Women entrepreneurs",
                "Includes convergence with Central/State subsidy programs",
                "Repayment period up to 7 years with 18 months moratorium"
            ]
        }
    ]

    @classmethod
    def evaluate_eligibility(
        cls,
        sector_code: str,
        project_cost: float,
        user_margin_available: float,
        category: SocialCategoryEnum = SocialCategoryEnum.GENERAL,
        is_rural: bool = True,
        applicant_age: int = 28,
        education_level: str = "10th_pass"
    ) -> List[MatchedSchemeResult]:
        """
        Matches and ranks all eligible government schemes for the given profile and business.
        """
        is_special = category in [
            SocialCategoryEnum.SC,
            SocialCategoryEnum.ST,
            SocialCategoryEnum.OBC,
            SocialCategoryEnum.WOMEN_ENTREPRENEUR,
            SocialCategoryEnum.MINORITY
        ]

        matched_results = []

        for s in cls.SCHEMES_DATABASE:
            reasons = []
            is_eligible = True

            # Sector Check
            if sector_code.lower() not in s["eligible_sectors"]:
                is_eligible = False
                reasons.append(f"Sector '{sector_code}' not supported by {s['scheme_code']}")

            # Age Check
            if applicant_age < s["min_age"]:
                is_eligible = False
                reasons.append(f"Minimum age required is {s['min_age']} years")

            # Category Check (e.g. Stand-Up India restricted to SC/ST/Women)
            if category.value not in s["eligible_categories"]:
                is_eligible = False
                reasons.append(f"Reserved exclusively for {', '.join(s['eligible_categories'])}")

            # Cost Check
            if project_cost < s["min_cost"] or project_cost > s["max_cost"]:
                is_eligible = False
                reasons.append(f"Project cost ₹{project_cost:,.0f} falls outside scheme range (₹{s['min_cost']:,.0f} - ₹{s['max_cost']:,.0f})")

            # Subsidy calculation
            if is_rural:
                subsidy_pct = s["special_rural_subsidy"] if is_special else s["general_rural_subsidy"]
            else:
                subsidy_pct = s["special_urban_subsidy"] if is_special else s["general_urban_subsidy"]

            subsidy_amount = min((subsidy_pct / 100.0) * project_cost, s["max_subsidy_cap"])

            # Margin calculation
            margin_pct = s["special_margin_pct"] if is_special else s["general_margin_pct"]
            margin_amount = (margin_pct / 100.0) * project_cost

            # Margin affordability check
            if user_margin_available < margin_amount:
                reasons.append(f"Available margin ₹{user_margin_available:,.0f} is lower than required ₹{margin_amount:,.0f}")

            net_loan = max(0.0, project_cost - margin_amount - subsidy_amount)

            if is_eligible:
                reasons.append("Fully eligible based on location, sector, category, and investment scale")

            matched_results.append(
                MatchedSchemeResult(
                    scheme_code=s["scheme_code"],
                    scheme_name=s["scheme_name"],
                    nodal_agency=s["nodal_agency"],
                    eligible=is_eligible,
                    subsidy_percentage=subsidy_pct,
                    subsidy_amount=round(subsidy_amount, 2),
                    margin_required_percentage=margin_pct,
                    margin_required_amount=round(margin_amount, 2),
                    net_bank_loan=round(net_loan, 2),
                    estimated_interest_rate=s["interest_rate"],
                    reasons=reasons,
                    benefits=s["benefits"]
                )
            )

        # Sort: Eligible first, then highest subsidy amount descending
        matched_results.sort(key=lambda x: (x.eligible, x.subsidy_amount), reverse=True)
        return matched_results

