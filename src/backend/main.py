from fastapi import FastAPI, UploadFile, File
from services.pdf_processor import PDFProcessor
from services.data_extractor import DataExtractor
from services.financial_analyzer import FinancialAnalyzer
from database.models import FinancialReport
from config import S3_CONFIG

app = FastAPI()

@app.post("/upload-report")
async def upload_report(file: UploadFile = File(...)):
    # Process uploaded PDF
    pdf_processor = PDFProcessor()
    extracted_text = await pdf_processor.process(file)
    
    # Extract financial data
    data_extractor = DataExtractor()
    financial_data = data_extractor.extract(extracted_text)
    
    # Store in database
    report = FinancialReport(**financial_data)
    await report.save()
    
    # Generate analysis
    analyzer = FinancialAnalyzer()
    analysis = analyzer.analyze(financial_data)
    
    return {"analysis": analysis} 