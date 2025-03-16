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
        self.raw_pdf_dir = Path("raw_pdf")
        
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
            
        return company_symbol, period, year, tags
    
    async def process_and_inject_documents(self) -> Dict[str, int]:
        """
        Process all PDF documents in the raw_pdf folder and inject them into the database.
        
        Returns:
            Dictionary with counts of processed, failed, and skipped documents
        """
        if not self.raw_pdf_dir.exists():
            logger.warning(f"Raw PDF directory {self.raw_pdf_dir} does not exist")
            return {"processed": 0, "failed": 0, "skipped": 0}
        
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        
        for file_path in self.raw_pdf_dir.glob("*.pdf"):
            try:
                filename = file_path.name
                company_symbol, period, year, tags = self.parse_filename(filename)
                
                # Extract text from PDF
                extraction_result = self.data_extractor.extract_text_from_file(str(file_path))
                
                if extraction_result["status"] != "success":
                    logger.error(f"Failed to extract text from {filename}: {extraction_result['message']}")
                    stats["failed"] += 1
                    continue
                
                # Read the extracted content
                processed_file_path = extraction_result["processed_file_path"]
                with open(processed_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Create report ID
                report_id = f"{company_symbol}_{period}_{year}"
                
                # Check if report already exists
                existing_report = await self.mongo_service.get_financial_report_by_report_id(report_id)
                if existing_report:
                    logger.info(f"Report {report_id} already exists, skipping")
                    stats["skipped"] += 1
                    continue
                
                # Create financial report object
                financial_report = FinancialReport(
                    report_id=report_id,
                    company=company_symbol,
                    type="Financial Statement",
                    period=f"{period} {year}",
                    date_created=datetime.now(),
                    status="final",
                    content=content,
                    tags=tags
                )
                
                # Save to database
                result = await self.mongo_service.create_financial_report(financial_report.dict(by_alias=True))
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


if __name__ == "__main__":
    import asyncio
    from src.db.mongo_services import MongoService
    from src.db.mongo_connect import db
    
    async def main():
        """Test the document injection functionality"""
        try:
            print("Starting document injection process...")
            # Initialize the MongoDB service
            mongo_service = MongoService()
            # Ensure indexes are created
            await mongo_service.ensure_indexes()
            
            # Create document injector
            doc_injector = DocumentInjector(mongo_service)
            
            # Process and inject documents
            stats = await doc_injector.process_and_inject_documents()
            
            # Print statistics
            print(f"Document injection complete:")
            print(f"  - Processed: {stats['processed']}")
            print(f"  - Failed: {stats['failed']}")
            print(f"  - Skipped: {stats['skipped']}")
            
            return True
        except Exception as e:
            print(f"Document injection failed: {str(e)}")
            return False
        finally:
            # Close database connection
            await db.close_db()
    
    # Run the main function
    asyncio.run(main())

