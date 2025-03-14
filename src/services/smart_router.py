"""
Smart Router Service for analyzing user queries and determining the appropriate processing path.
Routes queries to direct answers or document search based on query analysis.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
import re
from loguru import logger

from src.services.documents_search import DocumentSearchService
from src.services.llm_service import get_llm_service, LLMService

class SmartRouterService:
    """
    Service for routing user queries to the appropriate processing path.
    Analyzes queries to determine if they need document search or direct answers.
    """
    
    def __init__(self, 
                 llm_service: Optional[LLMService] = None,
                 search_service: Optional[DocumentSearchService] = None):
        """
        Initialize the smart router service.
        
        Args:
            llm_service: LLM service for query analysis and validation
            search_service: Document search service for retrieving relevant documents
        """
        self.llm_service = llm_service or get_llm_service()
        self.search_service = search_service or DocumentSearchService()
        logger.info("Initialized Smart Router service")
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a user query to determine routing strategy and extract parameters.
        
        Args:
            query: The user's query text
            
        Returns:
            Dictionary containing analysis results including:
            - needs_search: Whether the query requires document search
            - company_name: Extracted company name (if any)
            - document_type: Extracted document type (if any)
            - time_period: Extracted time period (if any)
            - search_terms: Key terms for document search
        """
        # Use LLM to analyze the query
        analysis_prompt = f"""
        Analyze the following user query and extract key information:
        
        Query: {query}
        
        Please determine:
        1. Does this query require searching financial documents? (yes/no)
        2. Is the user asking about a specific company? If yes, which one?
        3. Is the user asking about a specific document type (e.g., annual report, quarterly report, financial statement)?
        4. Is the user asking about a specific time period (e.g., Q1 2023, 2022)?
        5. What are the key search terms that should be used to find relevant documents?
        
        Format your response as JSON with the following fields:
        {{
            "needs_search": true/false,
            "company_name": "extracted company name or null",
            "document_type": "extracted document type or null",
            "time_period": "extracted time period or null",
            "search_terms": ["term1", "term2", ...]
        }}
        """
        
        try:
            # Generate analysis using LLM
            analysis_response = self.llm_service.generate_content(
                prompt=analysis_prompt,
                system_instruction="You are a financial query analyzer. Extract structured information from user queries."
            )
            
            if not analysis_response:
                logger.warning("Failed to analyze query, using default routing")
                return self._default_analysis(query)
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', analysis_response, re.DOTALL)
            if json_match:
                analysis_json = json_match.group(1)
            else:
                analysis_json = analysis_response
            
            import json
            try:
                analysis = json.loads(analysis_json)
                logger.info(f"Query analysis complete: {analysis}")
                return analysis
            except json.JSONDecodeError:
                logger.error(f"Failed to parse analysis response as JSON: {analysis_response}")
                return self._default_analysis(query)
                
        except Exception as e:
            logger.error(f"Error analyzing query: {str(e)}")
            return self._default_analysis(query)
    
    def _default_analysis(self, query: str) -> Dict[str, Any]:
        """Create a default analysis when LLM analysis fails."""
        return {
            "needs_search": True,
            "company_name": None,
            "document_type": None,
            "time_period": None,
            "search_terms": query.split()
        }
    
    def search_and_validate(self, query: str, analysis: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Search for relevant documents based on query analysis and validate results.
        
        Args:
            query: The original user query
            analysis: Query analysis dictionary from analyze_query
            
        Returns:
            Tuple containing:
            - List of relevant document dictionaries
            - Boolean indicating if search results are sufficient
        """
        # Construct search query from analysis
        search_query = query
        if analysis.get("company_name"):
            search_query += f" {analysis['company_name']}"
        if analysis.get("document_type"):
            search_query += f" {analysis['document_type']}"
        if analysis.get("time_period"):
            search_query += f" {analysis['time_period']}"
        
        # Search for documents
        search_results = self.search_service.search_documents(search_query)
        
        if not search_results:
            logger.info("No search results found")
            return [], False
        
        # Validate search results with LLM
        validation_prompt = f"""
        I need to determine if these search results are relevant to the user's query.
        
        User Query: {query}
        
        Search Results:
        {self._format_search_results(search_results)}
        
        Are these results relevant to the query? Please answer with "yes" or "no" and explain why.
        """
        
        validation_response = self.llm_service.generate_content(
            prompt=validation_prompt,
            system_instruction="You are a financial document validator. Determine if search results are relevant to user queries."
        )
        
        # Check if validation response indicates relevance
        is_relevant = "yes" in validation_response.lower() if validation_response else True
        
        logger.info(f"Search validation complete. Results relevant: {is_relevant}")
        return search_results, is_relevant
    
    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for validation prompt."""
        formatted = []
        for i, doc in enumerate(results, 1):
            formatted.append(f"Document {i}:")
            formatted.append(f"Report ID: {doc.get('report_id', 'Unknown')}")
            formatted.append(f"Company: {doc.get('company', 'Unknown')}")
            formatted.append(f"Type: {doc.get('type', 'Unknown')}")
            formatted.append(f"Period: {doc.get('period', 'Unknown')}")
            
            # Include a snippet of content
            content = doc.get('content', '')
            snippet = content[:200] + "..." if len(content) > 200 else content
            formatted.append(f"Content Snippet: {snippet}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the smart router.
        
        Args:
            query: The user's query text
            
        Returns:
            Dictionary containing processing results:
            - needs_search: Whether document search was performed
            - search_results: List of relevant documents (if search was performed)
            - analysis: Query analysis results
            - is_relevant: Whether search results are relevant
        """
        try:
            # Analyze the query
            analysis = self.analyze_query(query)
            
            # Determine if search is needed
            if analysis.get("needs_search", True):
                # Perform search and validation
                search_results, is_relevant = self.search_and_validate(query, analysis)
                
                return {
                    "needs_search": True,
                    "search_results": search_results,
                    "analysis": analysis,
                    "is_relevant": is_relevant
                }
            else:
                # No search needed, return analysis only
                return {
                    "needs_search": False,
                    "search_results": [],
                    "analysis": analysis,
                    "is_relevant": False
                }
                
        except Exception as e:
            logger.error(f"Error processing query through smart router: {str(e)}")
            return {
                "needs_search": False,
                "search_results": [],
                "analysis": self._default_analysis(query),
                "is_relevant": False,
                "error": str(e)
            }


# Singleton instance
default_smart_router = SmartRouterService()

def get_smart_router() -> SmartRouterService:
    """
    Get a smart router service instance.
    
    Returns:
        Smart router service instance
    """
    global default_smart_router
    return default_smart_router 