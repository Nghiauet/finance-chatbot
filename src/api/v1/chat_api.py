"""
Chat API endpoints for the finance chatbot.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, Query
from loguru import logger

from src.services.chatbot import chatbot_sessions, get_chatbot_service
from src.services.ai_service import get_ai_service
from src.api.v1.schemas import ChatQuery, ChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(query: ChatQuery):
    """Process a chat query with optional document context."""
    try:
        chatbot = get_chatbot_service(session_id=query.session_id)
        document_path = query.processed_file_path or query.file_path
        response = chatbot.process_query(query.query, document_path)
        return ChatResponse(answer=response, metadata={"session_id": chatbot.session_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat query: {e}")

@router.post("/smart-chat", response_model=ChatResponse)
async def smart_chat(query: ChatQuery):
    """
    Process a chat query using the smart router for enhanced document search and analysis.
    This endpoint uses AI to analyze the query, determine if document search is needed,
    and validate search results before generating a response.
    """
    try:
        ai_service = get_ai_service()
        response = ai_service.process_query(query)
        return response
    except Exception as e:
        logger.error(f"Error processing smart chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing smart chat query: {e}")
