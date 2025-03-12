from fastapi import APIRouter, UploadFile, File
from domain.services.pdf_processor import PDFProcessor
from domain.services.data_extractor import DataExtractor
from domain.services.financial_analyzer import FinancialAnalyzer
from domain.repositories.financial_report_repository import FinancialReportRepository

router = APIRouter(prefix="/v1/financial-reports")

@router.post("/upload")
async def upload_report(file: UploadFile = File(...)):
    # ... existing logic ... 