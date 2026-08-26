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

