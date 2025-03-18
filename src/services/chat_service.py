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
from src.core.config import llm_config

class ChatbotService:
    """Service for handling chatbot interactions with context from documents and financial reports."""
    def __init__(self, model_name: str = llm_config.default_model, session_id: str = None):
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
        11. answer questions in the same language as the question.
        12. if the money amount is too big, round it to the nearest million or billion.
        Financial reports, when available, are provided between [FINANCIAL REPORTS] tags.
        Context, when available, is provided between [CONTEXT] tags."""

    async def process_query(self, query: str, stock_symbol: Optional[str] = None, period: Optional[str] = None) -> str:
        """Process a user query with context from documents and/or financial reports.

        Args:
            query: User query.
            stock_symbol: Optional stock symbol or company identifier.
            period: Optional time period for financial reports.

        Returns:
            Response to the query.
        """
        try:
            # Get financial report content if stock symbol is provided
            financial_report_content = None
            if stock_symbol:
                financial_report = await self.mongo_service.get_financial_report_by_symbol_and_period(stock_symbol, period)
                if financial_report:
                    financial_report_content = financial_report.get('content', '')
                    logger.info(f"Retrieved financial report for {stock_symbol} ({period})")
                else:
                    logger.warning(f"No financial report found for symbol {stock_symbol} and period {period}")
            
            # Build the appropriate prompt based on available context
            if financial_report_content:
                prompt = self._build_prompt_with_financial_reports(financial_report_content, query)
            else:
                # If no financial report is found but stock symbol was provided, include that information in the prompt
                if stock_symbol:
                    prompt = self._build_prompt_for_missing_financial_report(stock_symbol, period, query)
                else:
                    prompt = self._build_prompt_without_context(query)
            
            response = self.llm_service.generate_content(
                prompt=prompt,
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

    def _build_prompt_with_financial_reports_and_history(self, statement_content: str, query: str) -> str:
        """Build prompt string with both financial reports and document context."""
        financial_reports = f"""[FINANCIAL REPORTS]\n{statement_content}\n[/FINANCIAL REPORTS]"""
        
        prompt_prefix = (
            "Based on the financial reports and additional context provided, please answer the following"
            " question:"
        )
        
        conversation_context = ""
        if self.conversation_history:
            conversation_context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(self.conversation_history)}\n[/CONTEXT]\n"""

        return f"""{financial_reports}\n\n{conversation_context}{prompt_prefix}\n{query}\n\nIf neither the financial reports nor the context contains information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge."""



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

    def _build_prompt_for_missing_financial_report(self, stock_symbol: str, period: Optional[str], query: str) -> str:
        """Build prompt string when financial report was requested but not found."""
        period_info = f" for period {period}" if period else ""
        context = f"""[CONTEXT]\nNo financial report was found for {stock_symbol}{period_info}.\n"""
        
        if self.conversation_history:
            context += f"Previous conversation:\n{chr(10).join(self.conversation_history)}\n"
        
        context += "[/CONTEXT]"
        
        prompt_prefix = (
            "The user is asking about a financial report that is not available. "
            "Please inform them that the requested financial data is not available "
            "and answer any general financial questions if possible:"
        )

        return f"""{context}\n{prompt_prefix}\n{query}"""



default_chatbot_service = ChatbotService()
chatbot_sessions: Dict[str, ChatbotService] = {}


def get_chatbot_service(
    model_name: str = llm_config.default_model, session_id: str = None
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
