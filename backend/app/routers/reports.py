from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.report import FinalReportSummary
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Final Report & Summary"])


@router.get("/{application_id}/summary", response_model=FinalReportSummary)
async def get_application_summary(
    application_id: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get the complete aggregated JSON summary of the business application.
    Combines Financials, Market Analysis, Scheme matching, and Feasibility into one unified response.
    """
    summary = await ReportService.generate_summary(db, application_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Application not found or no data available.")
    return summary


@router.get("/{application_id}/pdf")
async def get_application_pdf(
    application_id: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Generate and download a professional PDF Feasibility Report.
    """
    pdf_bytes = await ReportService.generate_pdf(db, application_id)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Application not found or PDF generation failed.")
        
    filename = f"RuralBiz_AI_Feasibility_Report_{application_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

