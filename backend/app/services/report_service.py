import io
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.application import BusinessApplication, FinancialPlan, FeasibilityAssessment
from app.models.user import User
from app.schemas.report import (
    FinalReportSummary,
    BusinessProfileSummary,
    FinancialSummaryDetails,
    SchemeSummaryDetails,
    MarketSummaryDetails,
    FeasibilitySummaryDetails,
    DataQualityDetails
)

logger = logging.getLogger(__name__)


class ReportService:
    @classmethod
    async def generate_summary(cls, db: AsyncSession, application_id: str) -> Optional[FinalReportSummary]:
        res = await db.execute(
            select(BusinessApplication)
            .options(
                selectinload(BusinessApplication.user),
                selectinload(BusinessApplication.business_type),
                selectinload(BusinessApplication.financial_plan),
                selectinload(BusinessApplication.feasibility_assessment)
            )
            .where(BusinessApplication.id == application_id)
        )
        app_obj = res.scalars().first()

        if not app_obj:
            return None

        # Build Profile
        user = app_obj.user
        bt = app_obj.business_type
        
        # Determine effective location
        village = app_obj.village_id or (user.village if user else "Unknown")
        district = app_obj.district_id or (user.district if user else "Unknown")
        state = user.state if user else "Unknown"
        
        profile = BusinessProfileSummary(
            business_category=bt.name_en if bt else "Unknown",
            location={"village": village, "block": "Unknown", "district": district, "state": state},
            available_margin_capital=app_obj.user_margin_available
        )

        fin_summary = None
        scheme_summary = None
        if app_obj.financial_plan:
            fp: FinancialPlan = app_obj.financial_plan
            fin_summary = FinancialSummaryDetails(
                project_cost=fp.total_project_cost,
                loan_amount=fp.net_bank_loan_required,
                interest_rate=fp.annual_interest_rate,
                loan_tenure_years=fp.loan_tenure_months // 12 if fp.loan_tenure_months else 0,
                moratorium_months=0,  # Could be derived from scheme
                monthly_emi=fp.monthly_emi_amount,
                quarterly_installment=fp.monthly_emi_amount * 3
            )
            scheme_summary = SchemeSummaryDetails(
                scheme_name=fp.matched_scheme_code,
                eligible=True if fp.subsidy_amount_eligible > 0 else False,
                maximum_loan=fp.net_bank_loan_required * 1.5  # placeholder logic based on ratio
            )

        feas_summary = None
        market_summary = None
        opportunities = []
        risks = []
        recommendation = {}
        
        if app_obj.feasibility_assessment:
            fa: FeasibilityAssessment = app_obj.feasibility_assessment
            feas_summary = FeasibilitySummaryDetails(
                overall_score=fa.overall_score,
                classification=fa.viability_rating.upper() if fa.viability_rating else "UNKNOWN",
                financial_score=fa.financial_viability_score,
                market_score=fa.market_demand_score,
                scheme_score=90.0,  # Assumed strong if matched
                risk_score=fa.risk_score
            )
            
            # Extract market summary from swot or just mock from scores if missing exact values
            # Usually the market engine would save exact population, but if not we show proxies
            market_summary = MarketSummaryDetails(
                reachable_population=5000,  # Standard proxy if not saved explicitly
                competitor_count=2,         # Proxy
                competition_level="MODERATE" if fa.market_demand_score > 60 else "HIGH",
                market_saturation_percentage=100 - fa.market_demand_score,
                market_opportunity_score=fa.market_demand_score,
                market_classification="HIGH_OPPORTUNITY" if fa.market_demand_score > 70 else "MODERATE"
            )
            
            if fa.swot_analysis:
                opportunities = fa.swot_analysis.get("opportunities", [])
                risks = fa.swot_analysis.get("threats", [])
                
            recommendation = {"primary_advice": fa.key_recommendations[0] if fa.key_recommendations else "Proceed with caution."}
        
        data_qual = DataQualityDetails(
            overall_confidence="MEDIUM",
            sources_used=["Internal DB", "Calculated"],
            limitations=["Proxy market data used where exact values missing"]
        )

        return FinalReportSummary(
            application_id=application_id,
            business_profile=profile,
            financial_summary=fin_summary,
            scheme_summary=scheme_summary,
            market_summary=market_summary,
            feasibility_summary=feas_summary,
            key_opportunities=opportunities,
            key_risks=risks,
            recommendation=recommendation,
            data_quality=data_qual
        )

    @classmethod
    async def generate_pdf(cls, db: AsyncSession, application_id: str) -> Optional[bytes]:
        summary = await cls.generate_summary(db, application_id)
        if not summary:
            return None
            
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError:
            logger.error("reportlab not installed.")
            return None

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = styles['Title']
        elements.append(Paragraph(f"RuralBiz AI - Business Feasibility Report", title_style))
        elements.append(Spacer(1, 12))

        # Profile
        h2 = styles['Heading2']
        elements.append(Paragraph("1. Business Profile", h2))
        profile_data = [
            ["Business Category", summary.business_profile.business_category],
            ["Village", summary.business_profile.location.get("village", "")],
            ["District", summary.business_profile.location.get("district", "")],
            ["Available Margin Capital", f"Rs. {summary.business_profile.available_margin_capital:,.2f}"]
        ]
        t = Table(profile_data, colWidths=[200, 300])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
                               ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # Financial Summary
        if summary.financial_summary:
            elements.append(Paragraph("2. Financial Structure", h2))
            fin = summary.financial_summary
            fin_data = [
                ["Total Project Cost", f"Rs. {fin.project_cost:,.2f}"],
                ["Bank Loan Required", f"Rs. {fin.loan_amount:,.2f}"],
                ["Interest Rate", f"{fin.interest_rate}%"],
                ["Tenure (Years)", str(fin.loan_tenure_years)],
                ["Monthly EMI", f"Rs. {fin.monthly_emi:,.2f}"]
            ]
            t2 = Table(fin_data, colWidths=[200, 300])
            t2.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
                                   ('GRID', (0,0), (-1,-1), 1, colors.black)]))
            elements.append(t2)
            elements.append(Spacer(1, 12))
            
        # Scheme Summary
        if summary.scheme_summary:
            elements.append(Paragraph("3. Recommended Scheme", h2))
            sch = summary.scheme_summary
            sch_data = [
                ["Scheme Name", sch.scheme_name],
                ["Eligible", "Yes" if sch.eligible else "No"]
            ]
            t3 = Table(sch_data, colWidths=[200, 300])
            t3.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
                                   ('GRID', (0,0), (-1,-1), 1, colors.black)]))
            elements.append(t3)
            elements.append(Spacer(1, 12))

        # Feasibility & Market
        if summary.feasibility_summary:
            elements.append(Paragraph("4. Feasibility & Market Analysis", h2))
            fs = summary.feasibility_summary
            ms = summary.market_summary
            
            mkt_str = f"Reachable Pop: {ms.reachable_population}, Competitors: {ms.competitor_count}, Saturation: {ms.market_saturation_percentage:.1f}%" if ms else "N/A"
            fs_data = [
                ["Overall Feasibility Score", f"{fs.overall_score:.1f} / 100"],
                ["Classification", fs.classification],
                ["Market Opportunity", mkt_str]
            ]
            t4 = Table(fs_data, colWidths=[200, 300])
            t4.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
                                   ('GRID', (0,0), (-1,-1), 1, colors.black)]))
            elements.append(t4)
            elements.append(Spacer(1, 12))
            
            # SWOT
            elements.append(Paragraph("Key Strengths & Opportunities", styles['Heading3']))
            for opp in summary.key_opportunities:
                elements.append(Paragraph(f"- {opp}", styles['Normal']))
            
            elements.append(Spacer(1, 6))
            elements.append(Paragraph("Key Risks & Threats", styles['Heading3']))
            for risk in summary.key_risks:
                elements.append(Paragraph(f"- {risk}", styles['Normal']))

        # Disclaimer
        elements.append(Spacer(1, 24))
        elements.append(Paragraph("Data Source & Disclaimer: This report uses a mix of deterministic financial calculations and local market proxy data. Generated by RuralBiz AI.", styles['Italic']))

        doc.build(elements)
        buffer.seek(0)
        return buffer.read()
