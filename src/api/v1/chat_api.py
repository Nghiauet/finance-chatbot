"""
Chat API endpoints for the finance chatbot.
"""
import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional, AsyncGenerator
import uuid

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from src.api.v1.schemas import ChatQuery, ChatResponse, ClearChatResponse
from src.services.chat_service import chatbot_sessions, get_chatbot_service

router = APIRouter()


@router.post("/chat-stream")
async def chat_stream(query: ChatQuery):
    """Process a chat query and stream the response."""
    try:
        chatbot = get_chatbot_service(session_id=query.session_id)
        logger.info(f"Session ID: {query.session_id}")
        logger.info(f"Query: {query.query}")

        response_stream = await chatbot.automation_flow_stream(
                query=query.query
            )

        return StreamingResponse(response_stream, media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat query: {e}")



@router.post("/clear-chat", response_model=ClearChatResponse)
async def clear_chat(session_id: str = Query(..., description="Session ID to clear")):
    """Clear the conversation history for a specific chat session."""
    try:
        chatbot = chatbot_sessions.get(session_id)
        if chatbot:
            chatbot.conversation_history = []
            logger.info(f"Chat history cleared for session {session_id}")
            return ClearChatResponse(status="success", message="Chat history cleared")
        else:
            logger.warning(f"Session {session_id} not found, nothing to clear")
            return ClearChatResponse(status="warning", message="Session not found")
    except Exception as e:
        logger.error(f"Error clearing chat history for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing chat history: {e}")


if __name__ == "__main__":

    async def main():
        """Test the chat endpoint."""
        from fastapi.testclient import TestClient

        from src.main import app  # Import your FastAPI app instance

        client = TestClient(app)

        chat_query = {
            "query": "analyse the financial statements of VNM",
            "company": "VNM",
            "period": "2024",
            "session_id": "test_session",
        }

        response = client.post("/api/v1/chat-stream", json=chat_query)

        if response.status_code == 200:
            for chunk in response.iter_text():
                if chunk:
                    print(chunk, end="", flush=True)
        else:
            print(f"Error: {response.status_code} - {response.text}")

    asyncio.run(main())
