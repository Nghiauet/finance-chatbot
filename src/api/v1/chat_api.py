"""
Chat API endpoints for the finance chatbot.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional, AsyncGenerator
import uuid

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from src.services.chat_service import chatbot_sessions, get_chatbot_service
from src.api.v1.schemas import ChatQuery, ChatResponse, ClearChatResponse
import json
import asyncio
router = APIRouter()

async def fake_generator():
    tokens = ["Hello", " world", "! ", "This", " is", " a", " streamed", " response", "."]
    for token in tokens:
        yield f"data: {json.dumps({'text': token})}\n\n"
        await asyncio.sleep(0.1)  # Simulate generation time

async def generate_stream(response_stream):
    for chunk in response_stream:
        print(chunk, end="", flush=True)
        yield f"data: {json.dumps({'text': chunk})}\n\n"

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


@router.post("/chat-stream")
async def chat_stream(query: ChatQuery):
    """Process a chat query and stream the response."""
    try:
        chatbot = get_chatbot_service(session_id=query.session_id)

        response_stream = await chatbot.process_query_stream(
            query=query.query,
            stock_symbol=query.company,
            period=query.period
        )
        return StreamingResponse(generate_stream(response_stream), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat query: {e}")

@router.post("/chat-stream-test")
async def chat_stream_test():
    return StreamingResponse(fake_generator(), media_type="text/event-stream")

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

if __name__ == "__main__":
    import asyncio

    async def main():
        # Test the chat endpoint
        from fastapi.testclient import TestClient
        from src.main import app  # Import your FastAPI app instance
        
        client = TestClient(app)
        
        # Example chat query
        chat_query = {
            "query": "analyse the financial statements of VNM",
            "company": "VNM",
            "period": "2024",
            "session_id": "test_session"
        }
        
        # Send the query to the /chat-stream endpoint
        response = client.post("/api/v1/chat-stream", json=chat_query)
        
        # Check if the request was successful
        if response.status_code == 200:
            for chunk in response.iter_text():
                if chunk:
                    print(chunk, end="", flush=True)
        else:
            print(f"Error: {response.status_code} - {response.text}")

    asyncio.run(main())
