"""
AI Service for handling user queries by combining document search and LLM capabilities.
Provides methods for searching documents and generating responses based on search results.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from pathlib import Path

from loguru import logger

from src.services.llm_service import get_llm_service, LLMService
from src.services.documents_search import DocumentSearchService
from src.services.smart_router import get_smart_router, SmartRouterService
from src.api.v1.schemas import ChatQuery, ChatResponse


class AIService:
    """Service for handling user queries with document search and LLM integration."""
    
    def __init__(self, 
                 llm_service: Optional[LLMService] = None,
                 search_service: Optional[DocumentSearchService] = None,
                 router_service: Optional[SmartRouterService] = None):
        """
        Initialize the AI service.
        
        Args:
            llm_service: LLM service instance for text generation
            search_service: Document search service instance
            router_service: Smart router service for query analysis
        """
        self.llm_service = llm_service or get_llm_service()
        self.search_service = search_service or DocumentSearchService()
        self.router_service = router_service or get_smart_router()
        logger.info("Initialized AI service with LLM, document search, and smart router capabilities")
    
    def process_query(self, chat_query: ChatQuery) -> ChatResponse:
        """
        Process a user query by searching relevant documents and generating a response.
        
        Args:
            chat_query: The chat query containing the user's question
            
        Returns:
            ChatResponse with the generated answer and metadata
        """
        try:
            # Use smart router to analyze and process the query
            router_result = self.router_service.process_query(chat_query.query)
            
            # Prepare metadata
            metadata = {
                "session_id": chat_query.session_id,
                "query_analysis": router_result["analysis"]
            }
            
            # Check if search was performed and results are relevant
            if router_result["needs_search"] and router_result["search_results"] and router_result["is_relevant"]:
                # Prepare context from search results
                context = self._prepare_context_from_search(router_result["search_results"])
                
                # Add source information to metadata
                metadata["sources"] = [doc.get("report_id", "Unknown") for doc in router_result["search_results"]]
                
                # Generate prompt with context
                prompt = self._create_prompt_with_context(chat_query.query, context)
                
                # Generate response using LLM
                system_instruction = (
                    "You are a financial analysis assistant. Answer questions based on the "
                    "provided financial document context. If you don't know the answer, say so."
                )
            else:
                # No search results or not relevant, generate response without document context
                prompt = self._create_prompt_without_context(chat_query.query)
                
                system_instruction = (
                    "You are a financial analysis assistant. Answer questions based on your "
                    "general knowledge about finance. If you don't know the answer, say so."
                )
            
            # Generate response
            llm_response = self.llm_service.generate_content(
                prompt=prompt,
                file_path=chat_query.file_path,
                system_instruction=system_instruction
            )
            
            return ChatResponse(
                answer=llm_response or "Sorry, I couldn't generate a response.",
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return ChatResponse(
                answer="An error occurred while processing your query.",
                metadata={"error": str(e)}
            )
    
    def _prepare_context_from_search(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Prepare context from search results for the LLM.
        
        Args:
            search_results: List of document search results
            
        Returns:
            Formatted context string
        """
        if not search_results:
            return "No relevant documents found."
        
        context_parts = []
        for i, doc in enumerate(search_results, 1):
            context_parts.append(f"Document {i}:")
            context_parts.append(f"Report ID: {doc.get('report_id', 'Unknown')}")
            context_parts.append(f"Company: {doc.get('company', 'Unknown')}")
            context_parts.append(f"Type: {doc.get('type', 'Unknown')}")
            context_parts.append(f"Period: {doc.get('period', 'Unknown')}")
            context_parts.append(f"Content: {doc.get('content', 'No content available')}")
            context_parts.append("")  # Empty line between documents
        
        return "\n".join(context_parts)
    
    def _create_prompt_with_context(self, query: str, context: str) -> str:
        """
        Create a prompt for the LLM with the user query and document context.
        
        Args:
            query: The user's query
            context: Document context from search results
            
        Returns:
            Formatted prompt string
        """
        return f"""
Please answer the following question based on the provided financial document context:

Question: {query}

Context:
{context}

Answer:
"""

    def _create_prompt_without_context(self, query: str) -> str:
        """
        Create a prompt for the LLM without document context.
        
        Args:
            query: The user's query
            
        Returns:
            Formatted prompt string
        """
        return f"""
Please answer the following financial question based on your knowledge:

Question: {query}

Answer:
"""


# Singleton instance for easy import
default_ai_service = AIService()


def get_ai_service() -> AIService:
    """
    Get an AI service instance.
    
    Returns:
        AI service instance
    """
    global default_ai_service
    return default_ai_service 