"""
Chatbot service for processing user queries with context from text files.
Uses Google's Gemini AI via the LLM service adapter and supports financial report querying.
"""
from __future__ import annotations

import os
import uuid
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain.document_loaders import TextLoader
from loguru import logger
from src.services.llm_service import LLMService, get_llm_service
from src.db.mongo_services import MongoService
from src.core.config import LLMConfig

class ChatbotService:
    """Service for handling chatbot interactions with context from documents and financial reports."""

    def __init__(self, model_name: str = LLMConfig.default_model, session_id: str = None):
        """
        Initialize the chatbot service.

        Args:
            model_name: Name of the Gemini model to use.
            session_id: Unique identifier for the chat session.
        """
        self.model_name = model_name
        self.session_id = session_id or str(uuid.uuid4())
        self.llm_service: LLMService = get_llm_service(model_name)
        self.mongo_service: MongoService = MongoService()
        self.vector_store = None
        self.conversation_history: List[str] = []
        logger.info(
            f"Initialized Chatbot service with model: {model_name}, session:"
            f" {self.session_id}"
        )

    def load_document(self, file_path: str) -> str | None:
        """
        Load a document and return its content as a string.

        Args:
            file_path: Path to the file to load.

        Returns:
            String containing the document content, or None if loading failed.
        """
        if not file_path:
            return None

        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in (".txt", ".md"):
                loader = TextLoader(file_path)
                documents = loader.load()
                text = "\n".join(doc.page_content for doc in documents)
                logger.info(f"Document loaded: {file_path}")
                return text
            else:
                logger.error(f"Unsupported file type: {file_ext}")
                return None

        except Exception as e:
            logger.error(f"Error loading document: {str(e)}")
            return None

    async def get_financial_report_by_symbol(self, symbol: str, period: Optional[str] = None) -> Optional[str]:
        """
        Retrieve financial report content for a specific company by stock symbol.

        Args:
            symbol: Stock symbol or company identifier
            period: Optional time period (e.g., "Q1 2024")

        Returns:
            Report content or None if not found
        """
        try:
            # Ensure MongoDB indexes
            await self.mongo_service.ensure_indexes()
            
            # Query parameters
            query = {}
            if symbol:
                # Make the search case insensitive and support partial matches
                query["$or"] = [
                    {"company": {"$regex": symbol, "$options": "i"}},
                    {"tags": {"$regex": symbol, "$options": "i"}},
                ]
            
            if period:
                query["period"] = {"$regex": period, "$options": "i"}
            
            # Get reports matching criteria
            reports = await self.mongo_service.list_financial_reports(
                limit=5,  # Limit to most recent reports
                sort_field="date_created",
                sort_order=-1,
                filters=query
            )
            
            if not reports:
                logger.warning(f"No financial reports found for symbol: {symbol}, period: {period}")
                return None
            
            # Combine report contents with metadata
            report_contents = []
            for report in reports:
                metadata = (
                    f"REPORT: {report.get('report_id', 'Unknown')}\n"
                    f"COMPANY: {report.get('company', 'Unknown')}\n"
                    f"PERIOD: {report.get('period', 'Unknown')}\n"
                    f"TYPE: {report.get('type', 'Unknown')}\n"
                    f"STATUS: {report.get('status', 'Unknown')}\n"
                    f"DATE: {report.get('date_created', datetime.now()).isoformat()}\n\n"
                )
                content = report.get('content', '')
                report_contents.append(f"{metadata}{content}")
            
            # Combine all reports, with newer reports first
            combined_content = "\n\n---\n\n".join(report_contents)
            logger.info(f"Retrieved {len(reports)} financial reports for {symbol}")
            return combined_content
        
        except Exception as e:
            logger.error(f"Error retrieving financial reports for {symbol}: {str(e)}")
            return None

    def get_system_instruction(self) -> str:
        """
        Get the system instruction for the chatbot.

        Returns:
            System instruction string.
        """
        return """You are a helpful financial assistant that can provide information based on financial reports,
        documents, or general knowledge. When answering:

        1. If financial report data is provided, prioritize information from those reports.
        2. If context is provided, use that as secondary information.
        3. If neither financial reports nor context has the answer but you know it, provide a general answer
           based on your financial knowledge.
        4. Be concise and clear in your explanations.
        5. Format financial data in a readable way.
        6. When discussing financial metrics, define them briefly before analyzing them.
        7. If you're unsure, acknowledge the limitations of your knowledge.
        8. If the user asks about a topic that is not related to finance, acknowledge that you are not able to answer that question.
        9. Always answer general financial questions like definitions of P/E ratio, ROI, or other common financial terms.
        10. If analyzing multiple reports, highlight trends and changes over time.

        Financial reports, when available, are provided between [FINANCIAL REPORTS] tags.
        Context, when available, is provided between [CONTEXT] tags."""

    async def process_query(self, query: str, file_path: Optional[str] = None, stock_symbol: Optional[str] = None, period: Optional[str] = None) -> str:
        """Process a user query with context from documents and/or financial reports.

        Args:
            query: User query.
            file_path: Optional path to a document for context.
            stock_symbol: Optional stock symbol or company identifier.
            period: Optional time period for financial reports.

        Returns:
            Response to the query.
        """
        try:
            # Use provided stock_symbol and period directly, no extraction from query
            # Get document content from file if provided
            document_content = self._get_document_content(file_path)
            
            # Get financial report content if stock symbol is provided
            financial_report_content = None
            if stock_symbol:
                financial_report_content = await self.get_financial_report_by_symbol(stock_symbol, period)
            
            # Build prompt based on available information
            if financial_report_content and document_content:
                prompt = self._build_prompt_with_financial_reports_and_context(
                    financial_report_content, document_content, query
                )
            elif financial_report_content:
                prompt = self._build_prompt_with_financial_reports(
                    financial_report_content, query
                )
            elif document_content:
                prompt = self._build_prompt_with_context(
                    document_content, query
                )
            else:
                prompt = self._build_prompt_without_context(query)

            response = self.llm_service.generate_content(
                prompt=prompt,
                file_path=file_path,
                system_instruction=self.get_system_instruction(),
            )

            if response:
                self.conversation_history.append(f"User: {query}")
                self.conversation_history.append(f"Chatbot: {response}")
                return response
            else:
                return "Sorry, I couldn't generate a response."

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return (
                "Sorry, an error occurred while processing your query:"
                f" {str(e)}"
            )
    
    def _extract_stock_symbol(self, query: str) -> Optional[str]:
        """Extract potential stock symbols from the query."""
        # Simple regex to find stock ticker patterns (e.g., AAPL, MSFT, GOOG)
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        matches = re.findall(ticker_pattern, query)
        
        # Exclude common words that might be mistaken for tickers
        common_words = {"A", "I", "IT", "IS", "BE", "AM", "PM", "THE", "AND", "OR", "FOR"}
        filtered_matches = [match for match in matches if match not in common_words]
        
        if filtered_matches:
            return filtered_matches[0]
        return None
    
    def _extract_period(self, query: str) -> Optional[str]:
        """Extract time periods from the query (e.g., Q1 2023, 2022, etc.)."""
        # Look for quarter patterns like Q1 2023
        quarter_pattern = r'Q[1-4]\s*\d{4}'
        quarter_match = re.search(quarter_pattern, query, re.IGNORECASE)
        if quarter_match:
            return quarter_match.group(0)
        
        # Look for year patterns
        year_pattern = r'\b20\d{2}\b'
        year_match = re.search(year_pattern, query)
        if year_match:
            return year_match.group(0)
        
        return None

    def _build_prompt_with_financial_reports(self, report_content: str, query: str) -> str:
        """Build prompt string with financial report content."""
        financial_reports = f"""[FINANCIAL REPORTS]\n{report_content}\n[/FINANCIAL REPORTS]"""
        prompt_prefix = (
            "Based on the financial reports provided, please answer the following"
            " question:"
        )
        
        conversation_context = ""
        if self.conversation_history:
            conversation_context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(self.conversation_history)}\n[/CONTEXT]\n"""

        return f"""{financial_reports}\n\n{conversation_context}{prompt_prefix}\n{query}\n\nIf the financial reports don't contain information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge."""

    def _build_prompt_with_financial_reports_and_context(self, report_content: str, document_content: str, query: str) -> str:
        """Build prompt string with both financial reports and document context."""
        financial_reports = f"""[FINANCIAL REPORTS]\n{report_content}\n[/FINANCIAL REPORTS]"""
        context = f"""[CONTEXT]\n{document_content}\n[/CONTEXT]"""
        
        prompt_prefix = (
            "Based on the financial reports and additional context provided, please answer the following"
            " question:"
        )
        
        conversation_context = ""
        if self.conversation_history:
            conversation_context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(self.conversation_history)}\n[/CONTEXT]\n"""

        return f"""{financial_reports}\n\n{context}\n\n{conversation_context}{prompt_prefix}\n{query}\n\nIf neither the financial reports nor the context contains information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge."""

    def _get_document_content(self, file_path: Optional[str]) -> Optional[str]:
        """Load document content from file path or retrieve from cache."""
        if not file_path:
            return None

        if (
            hasattr(self, "current_document_path")
            and self.current_document_path == file_path
        ):
            logger.info(
                "Using previously loaded document content for" f" {file_path}"
            )
            return self.current_document_content

        document_content = self.load_document(file_path)
        if document_content:
            self.current_document_path = file_path
            self.current_document_content = document_content
            logger.info(
                "Loaded and cached document content for" f" {file_path}"
            )
            return document_content
        else:
            return "Sorry, I couldn't load the document you provided."

    def _build_prompt_with_context(self, document_content: str, query: str) -> str:
        """Build prompt string with document context."""
        context = f"""[CONTEXT]\n{document_content}\n[/CONTEXT]"""
        prompt_prefix = (
            "Based on the above context, please answer the following"
            " question:"
        )
        if self.conversation_history:
            context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(self.conversation_history)}\n[/CONTEXT]"""
            prompt_prefix = (
                "Based on the previous conversation, answer the"
                " following question:"
            )

        return f"""{context}\n{prompt_prefix}\n{query}\n\nIf neither the context nor the previous conversation contains information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge."""

    def _build_prompt_without_context(self, query: str) -> str:
        """Build prompt string without document context."""
        prompt_prefix = (
            "You are a helpful financial assistant. Please answer the"
            " following question to the best of your ability:"
        )
        if self.conversation_history:
            context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(self.conversation_history)}\n[/CONTEXT]"""
            prompt_prefix = (
                "Based on the previous conversation, answer the"
                " following question:"
            )
        else:
            context = ""

        return f"""{context}\n{prompt_prefix}\n{query}"""



default_chatbot_service = ChatbotService()
chatbot_sessions: Dict[str, ChatbotService] = {}


def get_chatbot_service(
    model_name: str = LLMConfig.default_model, session_id: str = None
) -> ChatbotService:
    """Get a chatbot service instance.

    Args:
        model_name: Name of the model to use.
        session_id: Unique identifier for the chat session.

    Returns:
        Chatbot service instance.
    """
    global chatbot_sessions

    if not session_id:
        return default_chatbot_service

    if session_id not in chatbot_sessions:
        chatbot_sessions[session_id] = ChatbotService(model_name, session_id)

    return chatbot_sessions[session_id]
