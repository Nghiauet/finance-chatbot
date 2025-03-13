"""
Main FastAPI application for the finance chatbot backend.
"""
from fastapi import FastAPI, UploadFile, File
from src.backend.services.pdf_processor import PDFProcessor
from src.backend.services.data_extractor import DataExtractor
from src.backend.services.financial_analyzer import FinancialAnalyzer
from src.backend.database.models import FinancialReport
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api.v1 import chat_api

# Create FastAPI app
app = FastAPI(
    title="Finance Chatbot API",
    description="API for interacting with the finance chatbot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    chat_api.router,
    prefix="/api/v1",
    tags=["chat"]
)

@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {
        "status": "online",
        "message": "Finance Chatbot API is running",
        "docs_url": "/docs"
    }

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888) 