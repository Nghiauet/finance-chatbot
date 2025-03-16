"""
Document injection service for processing financial reports and saving them to the database.
Extracts company symbols and time periods from filenames and organizes data accordingly.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger
from bson import ObjectId

from src.services.data_extractor import DataExtractor
from src.services.llm_service import get_llm_service
from src.api.v1.schemas import FinancialReport


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
        self.raw_pdf_dir = Path("/home/nghiaph/nghiaph_workspace/experiments/finance-chatbot/data")
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
        # Skip "Baocaotaichinh" part
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
            
            # Extract text from PDF
            logger.debug(f"Extracting text from PDF: {file_path}")
            extraction_result = self.data_extractor.extract_text_from_pdf(str(file_path))
            logger.debug(f"Extraction result: {extraction_result}")
            if not extraction_result:
                logger.error(f"Failed to extract text from {filename}: {extraction_result['message']}")
                stats["failed"] += 1
                return stats
            
            # Read the extracted content
            processed_file_path = extraction_result["processed_file_path"]
            logger.debug(f"Reading extracted content from: {processed_file_path}")
            with open(processed_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug(f"Successfully read content, length: {len(content)} characters")
            
            # Create report ID
            report_id = f"{company_symbol}_{period}_{year}"
            logger.debug(f"Created report_id: {report_id}")
            
            # Check if report already exists
            logger.debug(f"Checking if report {report_id} already exists in database")
            existing_report = await self.mongo_service.get_financial_report_by_report_id(report_id)
            if existing_report:
                logger.info(f"Report {report_id} already exists, skipping")
                stats["skipped"] += 1
                return stats
            
            # Create financial report object
            logger.debug(f"Creating financial report object for {report_id}")
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
            logger.debug(f"Saving report {report_id} to database")
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
        
        logger.debug(f"Completed processing document {file_path} with stats: {stats}")
        return stats
    
    async def process_and_inject_documents(self) -> Dict[str, int]:
        """
        Process all PDF documents in the raw_pdf folder and inject them into the database.
        
        Returns:
            Dictionary with counts of processed, failed, and skipped documents
        """
        logger.debug(f"Starting batch processing of documents from {self.raw_pdf_dir}")
        if not self.raw_pdf_dir.exists():
            logger.warning(f"Raw PDF directory {self.raw_pdf_dir} does not exist")
            return {"processed": 0, "failed": 0, "skipped": 0}
        
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        
        pdf_files = list(self.raw_pdf_dir.glob("*.pdf"))
        logger.debug(f"Found {len(pdf_files)} PDF files to process")
        
        for file_path in pdf_files:
            logger.debug(f"Processing file: {file_path}")
            file_stats = await self.process_single_document(file_path)
            stats["processed"] += file_stats["processed"]
            stats["failed"] += file_stats["failed"]
            stats["skipped"] += file_stats["skipped"]
            logger.debug(f"Current cumulative stats: {stats}")
        
        logger.debug(f"Completed batch processing with final stats: {stats}")
        return stats


if __name__ == "__main__":
    import asyncio
    from src.db.mongo_services import MongoService
    from src.db.mongo_connect import db
    
    async def main():
        """Test the document injection functionality"""
        try:
            print("Starting document injection process...")
            logger.info("Starting document injection process for finance chatbot...")
            
            # Initialize the MongoDB service
            mongo_service = MongoService()
            logger.debug("MongoDB service initialized")
            
            # Create document injector
            doc_injector = DocumentInjector(mongo_service)
            logger.debug("Document injector created")
            
            # Test filename parsing
            test_filenames = [
                "MSH_Baocaotaichinh_Q4_2024_Congtyme.pdf",
                "PHN_Baocaotaichinh_Q1_2025_hopnhat.pdf",
                "VIC_Baocaotaichinh_Q2_2023.pdf",
                "INVALID_FORMAT.pdf"
            ]
            
            print("Testing filename parsing:")
            for filename in test_filenames:
                company_symbol, period, year, tags = doc_injector.parse_filename(filename)
                print(f"File: {filename}")
                print(f"  - Company: {company_symbol}")
                print(f"  - Period: {period}")
                print(f"  - Year: {year}")
                print(f"  - Tags: {tags}")
                print()
            
            # Ensure indexes are created
            await mongo_service.ensure_indexes()
            logger.debug("Database indexes ensured")
            
            # Test with specific file
            test_file_path = Path("/home/nghiaph/nghiaph_workspace/experiments/finance-chatbot/data/PHN_Baocaotaichinh_Q1_2025_hopnhat.pdf")
            logger.debug(f"Checking for test file at: {test_file_path}")
            if test_file_path.exists():
                logger.info(f"Processing specific test file: {test_file_path}")
                stats = await doc_injector.process_single_document(test_file_path)
                logger.debug(f"Test file processing completed with stats: {stats}")
                print(f"Single file processing complete:")
                print(f"  - Processed: {stats['processed']}")
                print(f"  - Failed: {stats['failed']}")
                print(f"  - Skipped: {stats['skipped']}")
            else:
                logger.error(f"Test file not found: {test_file_path}")
                print(f"Test file not found: {test_file_path}")
                
                # Process all documents as fallback
                logger.info("Falling back to processing all documents in directory...")
                logger.debug("Starting batch processing as fallback")
                stats = await doc_injector.process_and_inject_documents()
                logger.debug(f"Batch processing completed with stats: {stats}")
                
                # Print statistics
                print(f"Document injection complete:")
                print(f"  - Processed: {stats['processed']}")
                print(f"  - Failed: {stats['failed']}")
                print(f"  - Skipped: {stats['skipped']}")
            
            logger.info(f"Document injection complete - Processed: {stats['processed']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}")
            
            # Test flow for chatbot
            logger.info("Testing document retrieval flow for chatbot...")
            logger.debug("Starting chatbot flow test")
            if stats['processed'] > 0:
                # Test retrieving a processed document
                logger.debug("Attempting to retrieve a test report for PHN")
                test_report = await mongo_service.get_financial_report_by_company("PHN")
                if test_report:
                    logger.info(f"Successfully retrieved test report for chatbot flow: {test_report.get('report_id')}")
                    logger.debug(f"Retrieved report details: id={test_report.get('_id')}, company={test_report.get('company')}")
                else:
                    logger.warning("No test reports found for chatbot flow testing")
                    logger.debug("Database query returned no results for company=PHN")
            else:
                logger.warning("No documents were processed, skipping chatbot flow test")
            
            logger.debug("Main function completed successfully")
            return True
        except Exception as e:
            print(f"Document injection failed: {str(e)}")
            logger.error(f"Document injection failed: {str(e)}", exc_info=True)
            logger.debug(f"Stack trace for error: {str(e)}", exc_info=True)
            return False
        finally:
            # Close database connection
            logger.info("Closing database connection")
            logger.debug("Initiating database connection closure")
            await db.close_db()
            logger.debug("Database connection closed successfully")
    
    # Run the main function
    asyncio.run(main())
