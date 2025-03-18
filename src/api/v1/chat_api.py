"""
Chat API endpoints for the finance chatbot.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, Query
from loguru import logger

from src.services.chat_service import chatbot_sessions, get_chatbot_service
from src.api.v1.schemas import ChatQuery, ChatResponse, ClearChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(query: ChatQuery):
    """Process a chat query with optional document context and financial report parameters."""
    try:
        # Get or create a chatbot service for this session
        chatbot = get_chatbot_service(session_id=query.session_id)
        
        logger.debug(f"Chat input: {query}")

        # Process the query with company and period parameters
        # The chat service will now handle retrieving financial reports internally
        response = await chatbot.process_query(
            query=query.query, 
            stock_symbol=query.company,  
            period=query.period
        )
        
        logger.debug(f"Chatbot output: {response}")
        
        return ChatResponse(answer=response, metadata={"session_id": chatbot.session_id})
    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat query: {e}")

@router.post("/clear-chat", response_model=ClearChatResponse)
async def clear_chat(session_id: str = Query(..., description="Session ID to clear")):
    """Clear the conversation history for a specific chat session."""
    try:
        if session_id in chatbot_sessions:
            chatbot = chatbot_sessions[session_id]
            chatbot.conversation_history = []
            logger.info(f"Chat history cleared for session {session_id}")
            return ClearChatResponse(status="success", message="Chat history cleared")
        else:
            logger.warning(f"Session {session_id} not found, nothing to clear")
            return ClearChatResponse(status="warning", message="Session not found, nothing to clear")
    except Exception as e:
        logger.error(f"Error clearing chat history for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing chat history: {e}")
