"""Chatbot service for processing user queries with financial reports."""
from __future__ import annotations

import asyncio
import uuid
from typing import Dict, List, Optional, AsyncGenerator

from loguru import logger
from src.services.gemini_client import LLMService, get_llm_service_async
from src.db.mongo_services import MongoService
from src.core.config import llm_config
from src.services.tools import get_stock_information_tools, search_engine
from src.core import prompt
import json
from pydantic import BaseModel

class StockSymbol(BaseModel):
    """Stock symbol model."""
    symbol: str

class ChatSession:
    """Class representing a single chat session with conversation history."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation_history: List[str] = []
        self.history_lock = asyncio.Lock()  # Lock for thread-safe conversation history updates
        logger.info(f"Initialized chat session: {session_id}")
    
    async def add_to_history(self, user_query: str, bot_response: str):
        """Thread-safe method to add interactions to the history."""
        async with self.history_lock:
            self.conversation_history.append(f"User: {user_query}")
            self.conversation_history.append(f"Chatbot: {bot_response}")
    
    async def get_history(self):
        """Thread-safe method to get a copy of the conversation history."""
        async with self.history_lock:
            return self.conversation_history.copy()
    
    async def clear_history(self):
        """Thread-safe method to clear conversation history."""
        async with self.history_lock:
            self.conversation_history = []
            logger.info(f"Cleared history for session {self.session_id}")


class ChatbotService:
    """Service for handling multiple concurrent chatbot interactions using financial reports."""

    def __init__(self, model_name: str = llm_config.default_model):
        """Initialize the chatbot service."""
        self.model_name = model_name
        self.llm_service = None  # Will be initialized lazily
        self.mongo_service: MongoService = MongoService()
        self.sessions: Dict[str, ChatSession] = {}
        self.sessions_lock = asyncio.Lock()  # Lock for thread-safe session management
        logger.info(f"Initialized Chatbot service with model: {model_name}")

    async def _get_llm_service(self) -> LLMService:
        """Lazy initialization of LLM service."""
        if self.llm_service is None:
            self.llm_service = await get_llm_service_async(model_name=self.model_name)
        return self.llm_service

    async def get_or_create_session(self, session_id: str = None) -> str:
        """Get an existing session or create a new one."""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        async with self.sessions_lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = ChatSession(session_id)
                logger.info(f"Created new session: {session_id}")
        
        return session_id

    async def automation_flow_stream(self, query: str, session_id: str = None) -> AsyncGenerator[str, None]:
        """Get the financial report from the tools - optimized for concurrency."""
        # Ensure we have a valid session
        session_id = await self.get_or_create_session(session_id)
        session = self.sessions[session_id]
        
        llm_service = await self._get_llm_service()
        tools = [search_engine.search_information, get_stock_information_tools.get_stock_information_by_year]

        # Get a copy of the conversation history
        current_history = await session.get_history()
        
        prompt_with_context = prompt.build_prompt_with_tools_for_automation(query, current_history)
        
        # The generator function that will be returned
        async def generate_stream():
            # Use a local variable to store the complete response for this specific request
            full_response = ""
            
            # Get the response stream - this doesn't block other requests
            response_stream = llm_service.generate_content_with_tools(
                prompt=prompt_with_context, 
                operation_tools=tools, 
                system_instruction=prompt.SYSTEM_INSTRUCTION_FOR_AUTOMATION
            )
            
            # Process chunks as they become available
            async for chunk in response_stream:
                if chunk is not None:
                    full_response += chunk
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
            
            # Update conversation history after streaming is complete
            await session.add_to_history(query, full_response)
        
        # Return the generator function
        return generate_stream()
    
    async def clear_session(self, session_id: str) -> bool:
        """Clear the conversation history for a specific session."""
        async with self.sessions_lock:
            if session_id in self.sessions:
                await self.sessions[session_id].clear_history()
                return True
            return False


# Singleton instance of the ChatbotService
_chatbot_service = None
_service_lock = asyncio.Lock()

async def get_chatbot_service_async(model_name: str = llm_config.default_model) -> ChatbotService:
    """Get the singleton chatbot service instance with proper async locking."""
    global _chatbot_service
    
    async with _service_lock:
        if _chatbot_service is None:
            _chatbot_service = ChatbotService(model_name)
    
    return _chatbot_service


if __name__ == "__main__":
    import asyncio

    async def test_concurrent_requests():
        """Test function to simulate multiple concurrent requests."""
        # Get the singleton chatbot service
        chatbot = await get_chatbot_service_async()
        
        # Define multiple sessions and queries
        session1 = await chatbot.get_or_create_session("session1")
        session2 = await chatbot.get_or_create_session("session2")
        
        # Define different queries
        query1 = "Thông tin về những biến động gần đây của tập đoàn SCB"
        query2 = "Thông tin về những biến động gần đây của tập đoàn gelex và abbank"
        query3 = "Thông tin về những biến động gần đây của tập đoàn Vietcombank"
        query4 = "Thông tin về những biến động gần đây của tập đoàn BIDV"

        # Process queries concurrently
        async def process_query(session_id, query, delay=0):
            print(f"Starting query for session {session_id}: {query}")
            stream = await chatbot.automation_flow_stream(query, session_id)
            async for chunk in stream:
                # Simulate different consumer speeds
                if delay:
                    await asyncio.sleep(delay)
                print(f"Session {session_id} chunk: {chunk}")
            print(f"Query for session {session_id} complete")
        
        # Run all queries concurrently with different simulated consumer speeds
        await asyncio.gather(
            process_query(session1, query1, 0.1),
            process_query(session2, query2, 0),
            process_query(session1, query3, 0.05),
            process_query(session2, query4, 0.02)
        )
    
    # Run the test
    asyncio.run(test_concurrent_requests())