"""Chatbot service for processing user queries with financial reports."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional, AsyncGenerator

from loguru import logger
from src.services.llm_service import LLMService, get_llm_service
from src.db.mongo_services import MongoService
from src.core.config import llm_config
from src.services.tools import toolbox
from src.core import prompt
import json
from pydantic import BaseModel
class StockSymbol(BaseModel):
    """Stock symbol model."""
    symbol: str

class ChatbotService:
    """Service for handling chatbot interactions using financial reports."""

    def __init__(self, model_name: str = llm_config.default_model, session_id: str = None):
        """Initialize the chatbot service."""
        self.model_name = model_name
        self.session_id = session_id or str(uuid.uuid4())
        self.llm_service: LLMService = get_llm_service(model_name)
        self.mongo_service: MongoService = MongoService()
        self.conversation_history: List[str] = []
        logger.info(f"Initialized Chatbot service with model: {model_name}, session: {self.session_id}")

    async def process_query(self, query: str, stock_symbol: Optional[str] = None, period: Optional[str] = None) -> str:
        """Process a user query with context from financial reports."""
        try:
            prompt_text = await self._build_prompt(query, stock_symbol, period)
            response = self.llm_service.generate_content(
                prompt=prompt_text,
                system_instruction=prompt.get_system_instruction(),
            )

            if response:
                self.conversation_history.append(f"User: {query}")
                self.conversation_history.append(f"Chatbot: {response}")
                return response
            else:
                return "Sorry, I couldn't generate a response."

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"Sorry, an error occurred while processing your query: {e}"

    async def process_query_stream(self, query: str, stock_symbol: Optional[str] = None, period: Optional[str] = None):
        """Process a user query and stream the response."""
        try:
            prompt_text = await self._build_prompt(query, stock_symbol, period)
            response_stream = self.llm_service.generate_content_stream(
                prompt=prompt_text,
                system_instruction=prompt.get_system_instruction(),
            )
            full_response = ""

            async def generate_stream():
                nonlocal full_response  # Allow modification of full_response in the outer scope
                for chunk in response_stream:
                    full_response += chunk
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
            
                self.conversation_history.append(f"User: {query}")
                self.conversation_history.append(f"Chatbot: {full_response}")
            
            return generate_stream()

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise

    async def get_stock_symbols_from_query(self, query: str) -> Optional[List[str]]:
        """Get the stock symbol from the query."""
        prompt_text = prompt.build_prompt_for_extract_stock_symbol(query)
        stock_symbol_model = StockSymbol(symbol=query)
        stock_symbol = self.llm_service.generate_content_with_structured_output(prompt_text, stock_symbol_model)
        if stock_symbol:
            try:
                parsed_stock_symbol = stock_symbol.parsed
                list_stock_symbol = [stock_symbol.symbol for stock_symbol in parsed_stock_symbol]
                return list_stock_symbol
            except:
                return [stock_symbol.symbol]
        return None

    async def automation_flow(self, query: str) -> Optional[str]:
        """Get the financial report from the tools."""
        tools = [toolbox.get_stock_information]
        prompt_with_tools = prompt.build_prompt_with_tools_for_automation(query, self.conversation_history)
        response = self.llm_service.generate_content_with_tools(prompt = prompt_with_tools, operation_tools =  tools, system_instruction = prompt.SYSTEM_INSTRUCTION_FOR_AUTOMATION)
        return response
    
    async def automation_flow_stream(self, query: str) -> AsyncGenerator[str, None]:
        """Get the financial report from the tools."""
        tools = [toolbox.get_stock_information]

        prompt_with_context = prompt.build_prompt_with_tools_for_automation(query, self.conversation_history)
        response_stream = self.llm_service.generate_content_with_tools(prompt = prompt_with_context, operation_tools =  tools, system_instruction = prompt.SYSTEM_INSTRUCTION_FOR_AUTOMATION)
        full_response = ""
        async def generate_stream():
            nonlocal full_response  # Allow modification of full_response in the outer scope
            for chunk in response_stream:
                full_response += chunk
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            self.conversation_history.append(f"User: {query}")
            self.conversation_history.append(f"Chatbot: {full_response}")
        
        return generate_stream()

    async def _build_prompt(self, query: str, stock_symbol: Optional[str] = None, period: Optional[str] = None) -> str:
        """Build the appropriate prompt based on available context."""
        financial_report_content = None
        stock_price_info = None
        # if stock_symbol is None, get the stock symbol from the query
        if stock_symbol is None:
            stock_symbols = await self.get_stock_symbols_from_query(query)
            stock_symbol = stock_symbols[0] if stock_symbols else None
            logger.info(f"Stock symbol: {stock_symbol}")

        if stock_symbol:
            financial_report = await self.mongo_service.get_financial_report_by_symbol_and_period(stock_symbol, period)
            if financial_report:
                financial_report_content = financial_report.get('content', '')
                logger.info(f"Retrieved financial report for {stock_symbol} ({period})")
            else:
                logger.warning(f"No financial report found for symbol {stock_symbol} and period {period} in the database get from tools")
                financial_report = self.get_financial_report_from_tools(stock_symbol, period)
                if financial_report:
                    financial_report_content = financial_report
                    logger.info(f"Retrieved financial report for {stock_symbol} ({period}) from tools")
                else:
                    logger.warning(f"Could not retrieve financial report for {stock_symbol} ({period}) from tools") 
            
            
            # Fetch stock price
            try:
                stock_price = toolbox.get_stock_price_from_vnstock(stock_symbol)
                if stock_price:
                    stock_price_info = f"Current stock price of {stock_symbol}: {stock_price}"
                    logger.info(f"Retrieved stock price for {stock_symbol}: {stock_price}")
                else:
                    logger.warning(f"Could not retrieve stock price for {stock_symbol}")
            except Exception as e:
                logger.error(f"Error fetching stock price for {stock_symbol}: {e}")

        return self._build_prompt_based_on_context(financial_report_content, stock_price_info, stock_symbol, period, query)

    def _build_prompt_based_on_context(self, financial_report_content: Optional[str], stock_price_info: Optional[str], stock_symbol: Optional[str], period: Optional[str], query: str) -> str:
        """Build prompt based on available context."""
        if financial_report_content and stock_price_info:
            return prompt.build_prompt_with_financial_reports(
                financial_report_content, 
                query, 
                self.conversation_history, 
                stock_price_info
            )
        elif financial_report_content:
            return prompt.build_prompt_with_financial_reports(
                financial_report_content, 
                query, 
                self.conversation_history
            )
        elif stock_symbol and stock_price_info:
            return prompt.build_prompt_with_stock_price(
                stock_symbol, 
                period, 
                query, 
                stock_price_info, 
                self.conversation_history
            )
        elif stock_symbol:
            return prompt.build_prompt_for_missing_financial_report(
                stock_symbol, 
                period, 
                query, 
                self.conversation_history
            )
        else:
            return prompt.build_prompt_without_context(query, self.conversation_history)
    


default_chatbot_service = ChatbotService()
chatbot_sessions: Dict[str, ChatbotService] = {}


def get_chatbot_service(
    model_name: str = llm_config.default_model, session_id: str = None
) -> ChatbotService:
    """Get a chatbot service instance."""
    global chatbot_sessions

    if not session_id:
        return default_chatbot_service

    if session_id not in chatbot_sessions:
        chatbot_sessions[session_id] = ChatbotService(model_name, session_id)

    return chatbot_sessions[session_id]


if __name__ == "__main__":
    import asyncio

    async def main():
        chatbot = get_chatbot_service()
        query = "Lợi nhuận của TCB trong quý năm ngoái"


        response_stream = await chatbot.process_query(query)
        print(response_stream)

    asyncio.run(main())