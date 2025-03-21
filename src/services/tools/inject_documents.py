"""
Document injection service for processing financial reports and saving them to the database.
Extracts company symbols and time periods from filenames and organizes data accordingly.
"""
from __future__ import annotations

import os
import re
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger
from bson import ObjectId

from src.services.tools.data_extractor import DataExtractor
from src.api.v1.schemas import FinancialReport
from src.core.config import settings, get_logger

class DocumentInjector:
    """
    Service for processing financial documents from raw_pdf folder and injecting them into the database.
    Handles filename parsing to extract company symbols and reporting periods.
    """
    
    def __init__(self, mongo_service):
        """
        Initialize the DocumentInjector.
        
        Args:
            mongo_service: MongoDB service for database operations
        """
        self.mongo_service = mongo_service
        self.data_extractor = DataExtractor()
        self.raw_pdf_dir = Path(settings.RAW_PDF_DIR)
        self.converted_file_dir = Path(settings.CONVERTED_FILE_DIR)
        logger.debug(f"DocumentInjector initialized with raw_pdf_dir: {self.raw_pdf_dir}")
        
    def parse_filename(self, filename: str) -> Tuple[str, str, str, List[str]]:
        """
        Parse filename to extract company symbol, period, year, and additional tags.
        Expected format: SYMBOL_Baocaotaichinh_PERIOD_YEAR_additional_info
        Example: MSH_Baocaotaichinh_Q4_2024_Congtyme.pdf
        
        Args:
            filename: Name of the file to parse
            
        Returns:
            Tuple of (company_symbol, period, year, tags)
        """
        # Remove file extension
        base_name = os.path.splitext(filename)[0]
        
        # Split by underscore
        parts = base_name.split('_')
        
        if len(parts) < 4:
            logger.warning(f"Filename {filename} does not follow the expected format")
            return "UNKNOWN", "UNKNOWN", "UNKNOWN", []
        
        company_symbol = parts[0].upper()
        period = parts[2].upper()  # Q1, Q2, etc.
        year = parts[3]
        
        # Additional parts become tags
        tags = [company_symbol, period, year]
        if len(parts) > 4:
            tags.extend(parts[4:])
        
        logger.debug(f"Parsed filename {filename}: symbol={company_symbol}, period={period}, year={year}, tags={tags}")
        return company_symbol, period, year, tags
    
    async def process_single_document(self, file_path: Path) -> Dict[str, int]:
        """
        Process a single PDF document and inject it into the database.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with counts of processed, failed, and skipped documents
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        logger.debug(f"Starting to process document: {file_path}")
        
        try:
            filename = file_path.name
            company_symbol, period, year, tags = self.parse_filename(filename)
            logger.debug(f"Parsed file {filename} with symbol={company_symbol}, period={period}, year={year}")
            
            # Create report ID
            report_id = f"{company_symbol}_{period}_{year}"
            
            # Check if report already exists in database
            existing_report = await self.mongo_service.get_financial_report_by_report_id(report_id)
            if existing_report:
                logger.info(f"Report {report_id} already exists in database, skipping")
                stats["skipped"] += 1
                return stats
            
            # Check if file has already been processed
            expected_output_file = self.converted_file_dir / f"{os.path.splitext(filename)[0]}.txt"
            if expected_output_file.exists():
                logger.info(f"File {filename} has already been processed, using existing extraction")
                processed_file_path = expected_output_file
            else:
                # Extract text from PDF
                logger.info(f"Extracting text from PDF: {file_path}")
                extraction_result = self.data_extractor.extract_text_from_pdf(str(file_path))
                if not extraction_result["success"]:
                    logger.error(f"Failed to extract text from {filename}: {extraction_result['message']}")
                    stats["failed"] += 1
                    return stats
                processed_file_path = extraction_result["processed_file_path"]
            
            # Read the extracted content
            logger.debug(f"Reading extracted content from: {processed_file_path}")
            with open(processed_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Create financial report object
            financial_report = FinancialReport(
                report_id=report_id,
                company=company_symbol,
                type="Financial Statement",
                period=f"{period}-{year}",
                date_created=datetime.now(),
                status="final",
                content=content,
                tags=tags
            )
            
            # Save to database
            logger.info(f"Saving report {report_id} to database")
            result = await self.mongo_service.create_financial_report(financial_report.model_dump(by_alias=True))
            if result:
                logger.info(f"Successfully injected {report_id} into database")
                stats["processed"] += 1
            else:
                logger.error(f"Failed to inject {report_id} into database")
                stats["failed"] += 1
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {str(e)}")
            stats["failed"] += 1
        
        return stats
    
    async def process_and_inject_documents(self) -> Dict[str, int]:
        """
        Process all PDF documents in the raw_pdf folder and inject them into the database.
        
        Returns:
            Dictionary with counts of processed, failed, and skipped documents
        """
        logger.info(f"Starting batch processing of documents from {self.raw_pdf_dir}")
        if not self.raw_pdf_dir.exists():
            logger.warning(f"Raw PDF directory {self.raw_pdf_dir} does not exist")
            return {"processed": 0, "failed": 0, "skipped": 0}
        
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        
        pdf_files = list(self.raw_pdf_dir.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        for file_path in pdf_files:
            file_stats = await self.process_single_document(file_path)
            stats["processed"] += file_stats["processed"]
            stats["failed"] += file_stats["failed"]
            stats["skipped"] += file_stats["skipped"]
        
        logger.info(f"Completed batch processing with final stats: {stats}")
        return stats

if __name__ == "__main__":
    import asyncio
    from src.db.mongo_services import MongoService

    async def main():
        logger = get_logger(__name__)
        try:
            
            logger.info("Initializing MongoDB service")
            mongo_service = MongoService()


            logger.info("Initializing DocumentInjector")
            injector = DocumentInjector(mongo_service)

            logger.info("Starting document processing")
            stats = await injector.process_and_inject_documents()  # Added await here
            logger.info(f"Processing complete. Stats: {stats}")
        except Exception as e:
            logger.error(f"Error in main process: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    asyncio.run(main())