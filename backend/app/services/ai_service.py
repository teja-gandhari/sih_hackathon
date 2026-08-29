import os
import json
import logging
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.schemas.feasibility import AdvisoryQueryResponse, SWOTAnalysis

logger = logging.getLogger(__name__)


class GeminiAIService:
    """
    Multilingual AI Advisory Service powered by Google Gemini API.
    Supports English, Telugu (తెలుగు), and Hindi (हिंदी) with strictly grounded context.
    """

    SYSTEM_PROMPT = """You are RuralBiz AI, an empathetic, highly knowledgeable rural business advisor and micro-enterprise financial specialist.
You help rural and semi-urban entrepreneurs evaluate business feasibility, secure government loans (PMEGP, MUDRA, PMFME), manage seasonal cash flows, and build profitable enterprises.

Rules:
1. Respond in the user's requested language ({language_name}).
2. Use simple, supportive, easy-to-understand language. Avoid overwhelming corporate jargon.
3. GROUND your advice directly on the provided calculations: available margin, required loan, monthly EMI, subsidy, DSCR, and local market competition.
4. If there is a risk flag (e.g. Unviable purchasing power gap, seasonal harvest dip, or high informal competition), explain it clearly with actionable mitigation steps.
5. Provide a crisp, natural spoken script for Text-to-Speech (audio_tts_text) that sounds warm and encouraging.
"""

    @classmethod
    async def generate_advisory(
        cls,
        query_text: str,
        language: str,
        context_data: Dict[str, Any]
    ) -> AdvisoryQueryResponse:
        """
        Executes Gemini LLM with grounded prompt context, returning structured advisory.
        """
        lang_code = language.lower() if language else "te"
        lang_names = {
            "te": "Telugu (తెలుగు)",
            "hi": "Hindi (हिंदी)",
            "en": "English"
        }
        language_name = lang_names.get(lang_code, "Telugu (తెలుగు)")

        financials = context_data.get("financials", {})
        market = context_data.get("market_data", {})
        feasibility = context_data.get("feasibility", {})
        scheme = context_data.get("top_scheme", {})
        user_profile = context_data.get("user_profile", {})
        business = context_data.get("business", {})

        prompt = f"""
User Question: "{query_text}"
Language: {language_name}

Grounded Data Context:
- User: {user_profile.get('name', 'Entrepreneur')}, Location: {user_profile.get('location', 'Rural Telangana')}
- Available Margin Money: ₹{user_profile.get('available_margin', 50000):,.0f}
- Proposed Business: {business.get('name', 'Dairy Farming')} (Scale: {business.get('scale', 5)} units)
- Total Project Cost: ₹{financials.get('total_project_cost', 350000):,.0f}
- Recommended Scheme: {scheme.get('scheme_name', 'PMEGP')}
- Eligible Govt Subsidy: ₹{financials.get('subsidy_amount_eligible', 122500):,.0f} ({financials.get('subsidy_pct', 35)}%)
- Net Bank Loan Required: ₹{financials.get('net_bank_loan_required', 192500):,.0f}
- Monthly EMI: ₹{financials.get('monthly_emi_amount', 3945):,.0f}
- Monthly Expected Revenue: ₹{financials.get('projected_monthly_revenue', 28000):,.0f}
- Monthly Net Profit: ₹{financials.get('monthly_net_profit', 10055):,.0f}
- DSCR (Bankability Ratio): {financials.get('dscr_ratio', 2.5)}
- Break-Even: {financials.get('break_even_months', 8.2)} months
- Local Market Demand Index: {market.get('demand_index', 8.5)}/10
- Formal Competitors: {market.get('formal_competitor_count', 2)}, Informal Vendors: {market.get('estimated_informal_competitor_count', 4)}
- Purchasing Power Tier: {market.get('purchasing_power_tier', 'lower_middle')} (Daily MGNREGA Wage: ₹{market.get('mgnrega_daily_wage_rate', 300)})
- Market Gap Classification: {feasibility.get('market_gap_classification', 'viable_and_unserved')}
- Seasonal Warning: {feasibility.get('seasonal_cashflow_warning', 'Harvest dependent')}
- Feasibility Score: {feasibility.get('overall_score', 82)}/100 ({feasibility.get('viability_rating', 'high_feasibility')})

Please return a JSON response with:
{{
  "conversational_response": "Personalized 2-3 paragraph explanation in {language_name}",
  "audio_tts_text": "A warm, natural 3-4 sentence spoken summary in {language_name} for voice playback",
  "key_risks_and_mitigation": ["Risk 1 and practical rural solution", "Risk 2 and practical rural solution"],
  "swot_strengths": ["...", "..."],
  "swot_weaknesses": ["...", "..."],
  "swot_opportunities": ["...", "..."],
  "swot_threats": ["...", "..."]
}}
"""

        # Try executing via Gemini API if API key is present
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your_gemini_api_key_here":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name=settings.GEMINI_MODEL,
                    system_instruction=cls.SYSTEM_PROMPT.format(language_name=language_name)
                )
                
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                res_json = json.loads(response.text)
                return AdvisoryQueryResponse(
                    query_text=query_text,
                    language=lang_code,
                    conversational_response=res_json.get("conversational_response", ""),
                    audio_tts_text=res_json.get("audio_tts_text", ""),
                    feasibility_score=feasibility.get("overall_score", 80.0),
                    viability_rating=feasibility.get("viability_rating", "high_feasibility"),
                    market_gap_flag=feasibility.get("market_gap_classification", "viable_and_unserved"),
                    recommended_scheme=scheme.get("scheme_name", "PMEGP"),
                    estimated_subsidy=financials.get("subsidy_amount_eligible", 0.0),
                    estimated_loan=financials.get("net_bank_loan_required", 0.0),
                    estimated_monthly_emi=financials.get("monthly_emi_amount", 0.0),
                    key_risks_and_mitigation=res_json.get("key_risks_and_mitigation", []),
                    swot=SWOTAnalysis(
                        strengths=res_json.get("swot_strengths", []),
                        weaknesses=res_json.get("swot_weaknesses", []),
                        opportunities=res_json.get("swot_opportunities", []),
                        threats=res_json.get("swot_threats", [])
                    )
                )
            except Exception as e:
                logger.warning(f"Gemini API invocation failed ({e}), falling back to deterministic template synthesis.")

        # High-Quality Deterministic Fallback Generator in EN/TE/HI
        return cls._generate_fallback_advisory(
            query_text=query_text,
            lang_code=lang_code,
            context_data=context_data
        )

    @classmethod
    def _generate_fallback_advisory(
        cls,
        query_text: str,
        lang_code: str,
        context_data: Dict[str, Any]
    ) -> AdvisoryQueryResponse:
        """
        High-fidelity template synthesis in Telugu, Hindi, and English with exact math grounding.
        """
        financials = context_data.get("financials", {})
        scheme = context_data.get("top_scheme", {})
        feasibility = context_data.get("feasibility", {})
        business = context_data.get("business", {})
        user_profile = context_data.get("user_profile", {})
        market = context_data.get("market_data", {})

        margin = user_profile.get("available_margin", 50000.0)
        cost = financials.get("total_project_cost", 350000.0)
        subsidy = financials.get("subsidy_amount_eligible", 122500.0)
        loan = financials.get("net_bank_loan_required", 192500.0)
        emi = financials.get("monthly_emi_amount", 3945.0)
        profit = financials.get("monthly_net_profit", 10055.0)
        score = feasibility.get("overall_score", 82.0)
        scheme_name = scheme.get("scheme_code", "PMEGP")
        b_name = business.get("name", "డెయిరీ (Dairy)")

        if lang_code == "te":  # Telugu
            conversational = (
                f"మీ వద్ద ఉన్న ₹{margin:,.0f} మార్జిన్ మనీతో {b_name} వ్యాపారం మీకు చాలా అనుకూలంగా ఉంది. "
                f"మొత్తం ప్రాజెక్ట్ వ్యయం సుమారు ₹{cost:,.0f} అవుతుంది. {scheme_name} పథకం కింద మీకు ₹{subsidy:,.0f} వరకు "
                f"ప్రభుత్వ సబ్సిడీ లభిస్తుంది. మిగిలిన ₹{loan:,.0f} బ్యాంక్ రుణం ద్వారా లభిస్తుంది.\n\n"
                f"ప్రతినెలా EMI సుమారు ₹{emi:,.0f} కాగా, అన్ని ఖర్చులు మరియు EMI పోను ప్రతినెలా నికర లాభం సుమారు ₹{profit:,.0f} వరకు మిగులుతుంది. "
                f"స్థానిక మార్కెట్ డిమాండ్ బాగుంది. వేసవిలో పచ్చిమేత కొరత రాకుండా సైలేజ్ తయారీని ముందుగానే ప్రణాళిక చేసుకోండి."
            )
            tts_text = (
                f"నమస్కారం! మీ వద్ద ఉన్న ₹{margin:,.0f} మార్జిన్ మనీతో ఈ వ్యాపారం చాలా అనుకూలమైనది. "
                f"ప్రభుత్వ సబ్సిడీ ₹{subsidy:,.0f} లభిస్తుంది మరియు నెలవారీ EMI ₹{emi:,.0f} మాత్రమే. "
                f"మీ సాధ్యాసాధ్యాల స్కోరు {score:.0f} శాతంగా ఉంది."
            )
            risks = [
                "వేసవి కాలంలో పచ్చిమేత కొరత రాకుండా సైలేజ్ గడ్డి పద్ధతిని ఉపయోగించండి.",
                "వాతావరణ మార్పుల నుండి రక్షణ కోసం పశువులకు తప్పనిసరిగా బీమా చేయించండి.",
                "స్థానిక డెయిరీ కోఆపరేటివ్‌తో ముందస్తు పాల సరఫరా ఒప్పందం చేసుకోండి."
            ]
        elif lang_code == "hi":  # Hindi
            conversational = (
                f"आपके पास उपलब्ध ₹{margin:,.0f} मार्जिन मनी के साथ {b_name} का व्यवसाय बहुत उपयुक्त है। "
                f"कुल प्रोजेक्ट लागत लगभग ₹{cost:,.0f} होगी। {scheme_name} योजना के तहत आपको ₹{subsidy:,.0f} तक की "
                f"सरकारी सब्सिडी मिल सकती है। शेष ₹{loan:,.0f} बैंक लोन के रूप में मिलेगा।\n\n"
                f"मासिक EMI लगभग ₹{emi:,.0f} होगी और सभी खर्चे निकालने के बाद आपका मासिक शुद्ध लाभ लगभग ₹{profit:,.0f} होगा। "
                f"स्थानीय मांग मजबूत है, लेकिन गर्मियों में चारे की व्यवस्था पहले से कर लें।"
            )
            tts_text = (
                f"नमस्ते! आपके ₹{margin:,.0f} मार्जिन के साथ यह व्यवसाय बहुत अच्छा है। "
                f"आपको ₹{subsidy:,.0f} की सरकारी सब्सिडी मिल सकती है और मासिक EMI ₹{emi:,.0f} होगी। "
                f"आपकी व्यवहार्यता स्कोर {score:.0f} प्रतिशत है।"
            )
            risks = [
                "गर्मियों में हरे चारे की कमी से बचने के लिए साइलेज तकनीक अपनाएं।",
                "पशुओं का सरकारी योजना के तहत अनिवार्य बीमा करवाएं।",
                "दूध की बिक्री के लिए स्थानीय डेयरी संघ से पहले ही अनुबंध करें।"
            ]
        else:  # English
            conversational = (
                f"Based on your available margin of ₹{margin:,.0f}, starting a {b_name} enterprise is highly viable. "
                f"The estimated total project cost is ₹{cost:,.0f}. Under the {scheme_name} scheme, you qualify for "
                f"a government capital subsidy of ₹{subsidy:,.0f}. The balance ₹{loan:,.0f} will be financed via bank term loan.\n\n"
                f"Your monthly bank EMI will be approximately ₹{emi:,.0f}, leaving a projected net monthly profit of ₹{profit:,.0f}. "
                f"Local market absorption is strong. Ensure proper green fodder silage preparation for the summer season."
            )
            tts_text = (
                f"Hello! With your ₹{margin:,.0f} margin, this business is highly feasible. "
                f"You can get ₹{subsidy:,.0f} in government subsidy with a monthly EMI of ₹{emi:,.0f}. "
                f"Your overall feasibility score is {score:.0f} out of 100."
            )
            risks = [
                "Mitigate summer fodder scarcity through silage preservation techniques.",
                "Ensure comprehensive livestock/equipment insurance coverage under government schemes.",
                "Secure direct buyback linkages with local dairy cooperatives or mandis."
            ]

        swot = SWOTAnalysis(
            strengths=[
                f"High subsidy entitlement (₹{subsidy:,.0f}) lowering net debt burden.",
                f"Sound DSCR of {financials.get('dscr_ratio', 2.5):.2f} ensures comfortable bank repayment.",
                "Immediate local cash generation from day 1."
            ],
            weaknesses=[
                "Working capital sensitivity during dry summer/pre-harvest seasons.",
                "Requirement of daily cold chain handling or prompt mandi delivery."
            ],
            opportunities=[
                "High demand from nearby village clusters and local tea stalls/sweet shops.",
                "Expansion into organic vermicompost / by-products."
            ],
            threats=[
                f"Presence of {market.get('estimated_informal_competitor_count', 4)} informal unorganized local sellers.",
                "Feed and raw material price fluctuations."
            ]
        )

        return AdvisoryQueryResponse(
            query_text=query_text,
            language=lang_code,
            conversational_response=conversational,
            audio_tts_text=tts_text,
            feasibility_score=score,
            viability_rating=feasibility.get("viability_rating", "high_feasibility"),
            market_gap_flag=feasibility.get("market_gap_classification", "viable_and_unserved"),
            recommended_scheme=scheme.get("scheme_name", "PMEGP"),
            estimated_subsidy=subsidy,
            estimated_loan=loan,
            estimated_monthly_emi=emi,
            key_risks_and_mitigation=risks,
            swot=swot
        )

    # ─────────────────────────────────────────────────────────────────────────
    # AI Business Advisor Chat (POST /api/v1/advisory/chat)
    # ─────────────────────────────────────────────────────────────────────────

    CHAT_SYSTEM_PROMPT = (
        "RuralBiz AI is a multilingual rural micro-entrepreneurship business advisor. "
        "Provide practical, simple, clear, non-technical advice based only on the structured analysis provided. "
        "Do not fabricate data or guarantee business success. "
        "Clearly distinguish calculated facts from recommendations. "
        "If data is unavailable, explicitly state the limitation. "
        "All financial numbers, population data, competitor counts, and scheme eligibility "
        "come from the backend calculations — never invent or modify them. "
        "You only explain, advise, recommend and suggest strategies."
    )

    @classmethod
    async def build_advisory_context(
        cls,
        db: Any,
        request: Any,
    ) -> "AdvisoryContextResponse":
        """
        Gathers real grounded data from the Unified Feasibility Engine,
        Financial Engine, Scheme Router, and Market Engine.
        Returns a structured context for AI or frontend inspection.
        """
        from app.schemas.feasibility import (
            FeasibilityAnalyzeRequest,
            AdvisoryContextResponse,
        )
        from app.services.feasibility_engine import FeasibilityScoringEngine

        # Build a FeasibilityAnalyzeRequest from the chat request
        feas_req = FeasibilityAnalyzeRequest(
            application_id=getattr(request, "application_id", None),
            business_category=getattr(request, "business_category", "dairy"),
            available_margin_capital=getattr(request, "available_margin_capital", 50000.0),
            village=getattr(request, "village", "Village A"),
            district=getattr(request, "district", "Nalgonda"),
            state=getattr(request, "state", "Telangana"),
            category=getattr(request, "category", "obc"),
            is_rural=getattr(request, "is_rural", True),
            radius_km=getattr(request, "radius_km", 5.0),
        )

        feas_result = await FeasibilityScoringEngine.analyze_unified_feasibility(
            db=db,
            request=feas_req,
        )

        fin = feas_result.financial_summary or {}
        mkt = feas_result.market_summary or {}
        sch = feas_result.scheme_summary or {}

        return AdvisoryContextResponse(
            business_category=getattr(request, "business_category", "dairy") or "dairy",
            village=getattr(request, "village", "Village A") or "Village A",
            district=getattr(request, "district", "Nalgonda") or "Nalgonda",
            state=getattr(request, "state", "Telangana") or "Telangana",
            available_margin_capital=float(getattr(request, "available_margin_capital", 50000.0) or 50000.0),
            total_project_cost=fin.get("total_project_cost", 0.0),
            loan_amount=fin.get("total_project_cost", 0.0) * 0.90,
            selected_scheme=sch.get("matched_scheme_name", "PMEGP"),
            interest_rate=6.5 if fin.get("total_project_cost", 0) <= 140000.0 else 8.5,
            monthly_emi=fin.get("monthly_emi", 0.0),
            repayment_tenure_months=36 if fin.get("total_project_cost", 0) <= 140000.0 else 60,
            market_population=mkt.get("village_population"),
            reachable_population=mkt.get("village_population"),
            competitor_count=mkt.get("existing_competitors", 0),
            competition_level=mkt.get("competition_level", "LOW"),
            market_saturation_pct=mkt.get("market_saturation_percentage", 0.0),
            market_opportunity_score=feas_result.market_score,
            feasibility_score=feas_result.overall_feasibility_score,
            feasibility_classification=feas_result.classification,
            financial_strengths=feas_result.strengths,
            financial_risks=feas_result.key_risks,
            market_opportunities=feas_result.opportunities,
            market_risks=feas_result.key_risks,
            dscr_ratio=fin.get("dscr_ratio", 0.0),
            roi_percentage=fin.get("roi_percentage", 0.0),
            break_even_months=fin.get("break_even_months", 0.0),
            monthly_net_profit=fin.get("monthly_net_profit", 0.0),
        )

    @classmethod
    async def generate_chat_advisory(
        cls,
        db: Any,
        request: Any,
    ) -> "AdvisoryChatResponse":
        """
        Main entry point for POST /api/v1/advisory/chat.
        Gathers grounded context, builds a prompt, calls Gemini (or falls back),
        and returns a structured chat response.
        """
        from app.schemas.feasibility import (
            AdvisoryChatResponse,
            AdvisoryContextUsed,
        )

        question = request.question
        lang = (request.language or "en").lower()
        lang_names = {"te": "Telugu (తెలుగు)", "hi": "Hindi (हिंदी)", "en": "English"}
        lang_name = lang_names.get(lang, "English")

        # 1. Build grounded context from real backend engines
        try:
            context = await cls.build_advisory_context(db=db, request=request)
            context_used = AdvisoryContextUsed(financial=True, market=True, feasibility=True)
        except Exception as e:
            logger.error(f"Failed to build advisory context: {e}")
            return AdvisoryChatResponse(
                answer=(
                    "I'm sorry, I could not retrieve your business analysis data at this time. "
                    "Please ensure your application details are correctly submitted and try again."
                ),
                language=lang,
                context_used=AdvisoryContextUsed(),
                context_snapshot=None,
            )

        # 2. Build the grounded AI prompt
        prompt = cls._build_chat_prompt(question, lang_name, context)

        # 3. Try Gemini API
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if api_key and api_key not in ("", "your_gemini_api_key_here"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name=settings.GEMINI_MODEL,
                    system_instruction=cls.CHAT_SYSTEM_PROMPT,
                )
                response = model.generate_content(prompt)
                answer_text = response.text.strip()

                return AdvisoryChatResponse(
                    answer=answer_text,
                    language=lang,
                    context_used=context_used,
                    context_snapshot=context,
                )
            except Exception as e:
                logger.warning(f"Gemini chat API call failed ({e}), falling back to deterministic response.")

        # 4. Deterministic fallback
        fallback_answer = cls._generate_chat_fallback(question, lang, context)
        return AdvisoryChatResponse(
            answer=fallback_answer,
            language=lang,
            context_used=context_used,
            context_snapshot=context,
        )

    @classmethod
    def _build_chat_prompt(cls, question: str, lang_name: str, ctx: Any) -> str:
        """Build a grounded prompt with all real backend data injected."""
        return f"""User Question: "{question}"
Respond in: {lang_name}

=== GROUNDED BACKEND DATA (Source of Truth — Do NOT modify these numbers) ===

BUSINESS PROFILE:
- Business Category: {ctx.business_category}
- Location: {ctx.village}, {ctx.district}, {ctx.state}

FINANCIAL ANALYSIS (Calculated by Financial Engine):
- Available Margin Capital: ₹{ctx.available_margin_capital:,.0f}
- Total Feasible Project Cost: ₹{ctx.total_project_cost:,.0f}
- Maximum Loan Amount: ₹{ctx.loan_amount:,.0f}
- Selected Government Scheme: {ctx.selected_scheme}
- Interest Rate: {ctx.interest_rate}% per annum
- Monthly EMI: ₹{ctx.monthly_emi:,.0f}
- Repayment Tenure: {ctx.repayment_tenure_months} months
- Monthly Net Profit (after EMI): ₹{ctx.monthly_net_profit:,.0f}
- DSCR (Debt Service Coverage Ratio): {ctx.dscr_ratio:.2f}
- ROI: {ctx.roi_percentage:.1f}%
- Break-Even Period: {ctx.break_even_months:.0f} months

MARKET ANALYSIS (Calculated by Hyper-Local Market Engine):
- Reachable Population: {ctx.reachable_population:,} people
- Existing Competitors: {ctx.competitor_count}
- Competition Level: {ctx.competition_level}
- Market Saturation: {ctx.market_saturation_pct:.0f}%
- Market Opportunity Score: {ctx.market_opportunity_score:.0f}/100

OVERALL FEASIBILITY (Calculated by Unified Feasibility Engine):
- Feasibility Score: {ctx.feasibility_score:.0f}/100
- Classification: {ctx.feasibility_classification}

STRENGTHS:
{chr(10).join('- ' + s for s in ctx.financial_strengths)}

OPPORTUNITIES:
{chr(10).join('- ' + o for o in ctx.market_opportunities)}

RISKS:
{chr(10).join('- ' + r for r in ctx.financial_risks)}

=== INSTRUCTIONS ===
1. Answer the user's question using ONLY the data above.
2. Cite specific numbers from the analysis when relevant.
3. Provide practical, actionable advice for a rural micro-entrepreneur.
4. If asked about data you don't have, say so clearly.
5. Respond in {lang_name}.
6. Keep the response concise (2-4 paragraphs).
"""

    @classmethod
    def _generate_chat_fallback(cls, question: str, lang: str, ctx: Any) -> str:
        """Generate a deterministic, grounded fallback when Gemini API is unavailable."""
        cat = ctx.business_category.replace("_", " ").title()
        loc = f"{ctx.village}, {ctx.district}"

        if lang == "te":
            return (
                f"మీ {cat} వ్యాపారం {loc} లో ప్రారంభించడం గురించి విశ్లేషణ:\n\n"
                f"మీ సాధ్యాసాధ్యాల స్కోరు {ctx.feasibility_score:.0f}/100 ({ctx.feasibility_classification}). "
                f"మొత్తం ప్రాజెక్ట్ వ్యయం ₹{ctx.total_project_cost:,.0f}, "
                f"దీనిలో ₹{ctx.available_margin_capital:,.0f} మీ మార్జిన్ మనీ. "
                f"నెలవారీ EMI ₹{ctx.monthly_emi:,.0f} మరియు నికర లాభం ₹{ctx.monthly_net_profit:,.0f}. "
                f"DSCR {ctx.dscr_ratio:.2f} (బ్యాంక్ సిఫార్సు >= 1.40).\n\n"
                f"మార్కెట్‌లో {ctx.competitor_count} పోటీదారులు ఉన్నారు, "
                f"సంతృప్తత {ctx.market_saturation_pct:.0f}%. "
                f"మార్కెట్ అవకాశ స్కోరు {ctx.market_opportunity_score:.0f}/100.\n\n"
                f"ప్రస్తుతం AI సేవ అందుబాటులో లేదు. మరింత వ్యక్తిగత సలహా కోసం తర్వాత ప్రయత్నించండి."
            )
        elif lang == "hi":
            return (
                f"आपके {cat} व्यवसाय का {loc} में विश्लेषण:\n\n"
                f"आपकी व्यवहार्यता स्कोर {ctx.feasibility_score:.0f}/100 ({ctx.feasibility_classification}) है। "
                f"कुल प्रोजेक्ट लागत ₹{ctx.total_project_cost:,.0f}, "
                f"जिसमें आपकी मार्जिन मनी ₹{ctx.available_margin_capital:,.0f} है। "
                f"मासिक EMI ₹{ctx.monthly_emi:,.0f} और शुद्ध लाभ ₹{ctx.monthly_net_profit:,.0f}। "
                f"DSCR {ctx.dscr_ratio:.2f} (बैंक सिफारिश >= 1.40).\n\n"
                f"बाजार में {ctx.competitor_count} प्रतिस्पर्धी हैं, "
                f"संतृप्ति {ctx.market_saturation_pct:.0f}%। "
                f"बाजार अवसर स्कोर {ctx.market_opportunity_score:.0f}/100.\n\n"
                f"वर्तमान में AI सेवा उपलब्ध नहीं है। अधिक व्यक्तिगत सलाह के लिए बाद में प्रयास करें।"
            )
        else:
            return (
                f"Analysis of your {cat} business in {loc}:\n\n"
                f"Your overall feasibility score is {ctx.feasibility_score:.0f}/100 ({ctx.feasibility_classification}). "
                f"Total project cost is ₹{ctx.total_project_cost:,.0f}, "
                f"with your margin contribution of ₹{ctx.available_margin_capital:,.0f}. "
                f"Monthly EMI is ₹{ctx.monthly_emi:,.0f} and projected net profit is ₹{ctx.monthly_net_profit:,.0f}. "
                f"DSCR is {ctx.dscr_ratio:.2f} (bank benchmark >= 1.40).\n\n"
                f"There are {ctx.competitor_count} existing competitors in the area, "
                f"with market saturation at {ctx.market_saturation_pct:.0f}%. "
                f"Market opportunity score is {ctx.market_opportunity_score:.0f}/100.\n\n"
                f"The AI advisory service is currently unavailable. "
                f"The above data is from verified backend calculations. "
                f"Please try again later for personalized AI-powered recommendations."
            )


