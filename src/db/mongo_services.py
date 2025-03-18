# Import required modules
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from src.db.mongo_connect import db
from src.api.v1.schemas import FinancialReport
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from pymongo import ASCENDING, DESCENDING, TEXT
from src.core.config import settings, get_logger
import base64
import hashlib
import asyncio

# Initialize logger
logger = get_logger("db.mongo_connect")

class MongoService:
    def __init__(self):
        self._database = db.db
        self._indexes_ensured = False
        logger.debug("MongoService initialized")

    async def ensure_indexes(self):
        """Ensure database indexes are created"""
        if self._indexes_ensured:
            return
        await self._ensure_index()
        self._indexes_ensured = True
        logger.debug("Database indexes ensured")
    
    async def _ensure_index(self):
        """Create necessary indexes for collections"""
        # Financial reports indexes
        await self._database.financial_reports.create_index([("report_id", ASCENDING)], unique=True)
        await self._database.financial_reports.create_index([("company", ASCENDING)])
        await self._database.financial_reports.create_index([("type", ASCENDING)])
        await self._database.financial_reports.create_index([("period", ASCENDING)])
        await self._database.financial_reports.create_index([("status", ASCENDING)])
        await self._database.financial_reports.create_index([("tags", ASCENDING)])
        await self._database.financial_reports.create_index([("content", TEXT)])
        
        # Add indexes for user collection if needed
        await self._database.users.create_index([("email", ASCENDING)], unique=True)
        
        logger.info("Database indexes created successfully")
    
    # Financial Report CRUD Operations
    
    async def create_financial_report(self, report: FinancialReport) -> str:
        """
        Create a new financial report document
        
        Args:
            report: FinancialReport model instance or dictionary
            
        Returns:
            str: Inserted document ID
        
        Raises:
            HTTPException: If insertion fails
        """
        try:
            # Handle both Pydantic model and dictionary inputs
            if hasattr(report, 'model_dump'):
                report_dict = report.model_dump(by_alias=True, exclude={"id"})
            else:
                # If report is already a dictionary
                report_dict = report
                
            result = await self._database.financial_reports.insert_one(report_dict)
            logger.info(f"Financial report created with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except DuplicateKeyError:
            report_id = report.report_id if hasattr(report, 'report_id') else report.get('report_id', 'unknown')
            logger.error(f"Duplicate report_id found: {report_id}")
            raise HTTPException(status_code=400, detail=f"Report with ID {report_id} already exists")
        except Exception as e:
            logger.error(f"Error creating financial report: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    async def get_financial_report_by_report_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a financial report by its report_id
        
        Args:
            report_id: Unique identifier for the report
            
        Returns:
            Optional[Dict]: Report document or None if not found
        """
        report = await self._database.financial_reports.find_one({"report_id": report_id})
        if report:
            return report
        return None
    
    async def get_financial_report_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a financial report by its MongoDB _id
        
        Args:
            id: MongoDB ObjectId as string
            
        Returns:
            Optional[Dict]: Report document or None if not found
        """
        try:
            report = await self._database.financial_reports.find_one({"_id": ObjectId(id)})
            if report:
                return report
            return None
        except Exception as e:
            logger.error(f"Error retrieving report by id {id}: {str(e)}")
            return None
    
    async def update_financial_report(self, report_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update a financial report
        
        Args:
            report_id: Unique identifier for the report
            update_data: Dictionary of fields to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Exclude _id from update data if present
            if "_id" in update_data:
                del update_data["_id"]
                
            result = await self._database.financial_reports.update_one(
                {"report_id": report_id},
                {"$set": update_data}
            )
            
            if result.matched_count > 0:
                logger.info(f"Financial report {report_id} updated successfully")
                return True
            else:
                logger.warning(f"Financial report {report_id} not found for update")
                return False
        except Exception as e:
            logger.error(f"Error updating report {report_id}: {str(e)}")
            return False
    
    async def delete_financial_report(self, report_id: str) -> bool:
        """
        Delete a financial report
        
        Args:
            report_id: Unique identifier for the report
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            result = await self._database.financial_reports.delete_one({"report_id": report_id})
            if result.deleted_count > 0:
                logger.info(f"Financial report {report_id} deleted successfully")
                return True
            else:
                logger.warning(f"Financial report {report_id} not found for deletion")
                return False
        except Exception as e:
            logger.error(f"Error deleting report {report_id}: {str(e)}")
            return False
    
    # Query operations
    
    async def list_financial_reports(
        self, 
        skip: int = 0, 
        limit: int = 100,
        sort_field: str = "date_created",
        sort_order: int = -1,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List financial reports with optional filtering and sorting
        
        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort_field: Field to sort by
            sort_order: Sort direction (1 for ascending, -1 for descending)
            filters: Optional query filters
            
        Returns:
            List[Dict]: List of financial report documents
        """
        query = filters or {}
        
        cursor = self._database.financial_reports.find(query)
        cursor = cursor.sort(sort_field, sort_order).skip(skip).limit(limit)
        
        reports = await cursor.to_list(length=limit)
        return reports
    
    async def search_financial_reports(self, search_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search financial reports using text search
        
        Args:
            search_text: Text to search for
            limit: Maximum number of results to return
            
        Returns:
            List[Dict]: List of matching financial report documents
        """
        try:
            cursor = self._database.financial_reports.find(
                {"$text": {"$search": search_text}},
                {"score": {"$meta": "textScore"}}
            )
            cursor = cursor.sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            reports = await cursor.to_list(length=limit)
            return reports
        except Exception as e:
            logger.error(f"Error searching reports: {str(e)}")
            return []
    

    

    async def get_financial_report_by_symbol_and_period(self, symbol: str, period: Optional[str] = None) -> Dict:
        """
        Retrieve a financial report by company symbol and period.
        
        Args:
            symbol: The company stock symbol
            period: Optional period (e.g., "Q1-2023")
            
        Returns:
            The financial report document or None if not found
        """
        try:
            # Create a case-insensitive query for the company symbol
            # This will match regardless of case (upper, lower, mixed)
            query = {"company": {"$regex": f"^{symbol}$", "$options": "i"}}
            if period:
                query["period"] = {"$regex": f"^{period}$", "$options": "i"}
            
            logger.info(f"Searching for financial report with query: {query}")
            report = await self._database.financial_reports.find_one(query)
            
            if report:
                logger.info(f"Found financial report for {symbol} ({period})")
                return report
            else:
                # Try a more flexible search if exact match fails
                fallback_query = {"company": {"$regex": symbol, "$options": "i"}}
                if period:
                    fallback_query["period"] = {"$regex": period, "$options": "i"}
                
                logger.info(f"Trying fallback query: {fallback_query}")
                report = await self._database.financial_reports.find_one(fallback_query)
                
                if report:
                    logger.info(f"Found financial report for {symbol} with fallback query")
                    return report
                else:
                    logger.warning(f"No financial report found for {symbol} ({period})")
                    return None
        except Exception as e:
            logger.error(f"Error retrieving financial report: {str(e)}")
            return None

async def test_mongo_service():
    """Test the MongoDB service functionality"""
    try:
        # Initialize the service
        mongo_service = MongoService()
        logger.info("Testing MongoDB service...")
        
        # Ensure indexes
        await mongo_service.ensure_indexes()
        logger.info("Indexes created successfully")
        
        # Test listing reports
        reports = await mongo_service.list_financial_reports(limit=5)
        logger.info(f"Found {len(reports)} financial reports")
        
        # Test searching
        if reports:
            # Get a sample company name from the first report
            sample_company = reports[0].get("company", "Unknown")
            logger.info(f"Searching for reports from company: {sample_company}")
            company_reports = await mongo_service.get_reports_by_company(sample_company)
            logger.info(f"Found {len(company_reports)} reports for {sample_company}")
            
            # Test text search if there are any reports
            search_results = await mongo_service.search_financial_reports("financial")
            logger.info(f"Text search found {len(search_results)} reports")
        
        logger.info("MongoDB service tests completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error testing MongoDB service: {str(e)}")
        return False

async def main():
    """Main function to run all tests"""
    try:
        logger.info("Starting MongoDB service tests")
        await test_mongo_service()
        logger.info("MongoDB service tests completed")
        
        # Test search for MSH for Q4-2024 - moved inside the main async function
        mongo_service = MongoService()
        report = await mongo_service.get_financial_report_by_symbol_and_period("MSH", "Q4-2024")
        logger.info(f"Report: {report}")
        
    except Exception as e:
        logger.error(f"Error during tests: {e}")

if __name__ == "__main__":
    """Run the MongoDB service tests when module is executed directly"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
