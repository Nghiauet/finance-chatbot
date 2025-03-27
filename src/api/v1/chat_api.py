"""
Chat API endpoints for the finance chatbot with improved output readability.
"""
import asyncio
import os
import json
import time
import random
import textwrap
from pathlib import Path
from typing import Any, Dict, Optional, AsyncGenerator
import uuid

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from src.api.v1.schemas import ChatQuery, ChatResponse, ClearChatResponse
from src.services.chat_service import get_chatbot_service_async

router = APIRouter()


@router.post("/chat-stream")
async def chat_stream(query: ChatQuery):
    """Process a chat query and stream the response."""
    try:
        # Get the singleton chatbot service
        chatbot = await get_chatbot_service_async()
        
        logger.info(f"Session ID: {query.session_id}")
        logger.info(f"Query: {query.query}")
        logger.info(f"Request from user: {query.user_id if hasattr(query, 'user_id') else 'Unknown'}")

        # Use the session_id from the query
        response_stream = await chatbot.automation_flow_stream(
            query=query.query,
            session_id=query.session_id
        )

        return StreamingResponse(response_stream, media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat query: {e}")


@router.post("/clear-chat", response_model=ClearChatResponse)
async def clear_chat(session_id: str = Query(..., description="Session ID to clear")):
    """Clear the conversation history for a specific chat session."""
    try:
        chatbot = await get_chatbot_service_async()
        success = await chatbot.clear_session(session_id)
        
        if success:
            logger.info(f"Chat history cleared for session {session_id}")
            return ClearChatResponse(status="success", message="Chat history cleared")
        else:
            logger.warning(f"Session {session_id} not found, nothing to clear")
            return ClearChatResponse(status="warning", message="Session not found")
    except Exception as e:
        logger.error(f"Error clearing chat history for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing chat history: {e}")


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def parse_sse_data(data):
    """Parse SSE data and handle both string and bytes inputs."""
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    
    result = ""
    # Split by "data:" to handle multiple SSE events in one chunk
    parts = data.split("data:")
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        try:
            parsed = json.loads(part)
            if "text" in parsed:
                result += parsed["text"]
        except json.JSONDecodeError:
            # Skip malformed JSON or non-JSON parts
            continue
            
    return result


async def simulate_user_request(client, user_id, query, session_id=None):
    """Simulate a user making a request to the chat API with better output formatting."""
    if not session_id:
        session_id = f"session_{user_id}"
    
    # Print user query in a nice format
    print(f"\n{Colors.BOLD}{Colors.BLUE}┌─ User {user_id} Request ───────────────────────────────────┐{Colors.ENDC}")
    print(f"{Colors.BLUE}│ Session: {session_id}{' ' * (50 - len(session_id))}{Colors.BLUE}│{Colors.ENDC}")
    
    # Format and print the query
    wrapped_query = textwrap.fill(query, width=50)
    for line in wrapped_query.split('\n'):
        print(f"{Colors.BLUE}│ Query: {line}{' ' * (43 - len(line))}{Colors.BLUE}│{Colors.ENDC}")
    
    print(f"{Colors.BLUE}└──────────────────────────────────────────────────────┘{Colors.ENDC}")
    
    chat_query = {
        "query": query,
        "session_id": session_id
    }
    
    # Process the request
    start_time = time.time()
    try:
        response = await client.post("/api/v1/chat-stream", json=chat_query, timeout=60.0)
        
        if response.status_code == 200:
            print(f"{Colors.GREEN}✓ Response started in {time.time() - start_time:.2f}s{Colors.ENDC}")
            
            # Process and display the streaming response
            full_response = ""
            chunk_count = 0
            
            print(f"{Colors.CYAN}┌─ Response ─────────────────────────────────────────────┐{Colors.ENDC}")
            
            # Process the streaming response
            async for chunk in response.aiter_bytes():
                text = parse_sse_data(chunk)
                if text:
                    full_response += text
                    chunk_count += 1
                    
                    # Format the text chunks for display
                    wrapped_text = textwrap.fill(text, width=55)
                    for line in wrapped_text.split('\n'):
                        print(f"{Colors.CYAN}│{Colors.ENDC} {line}{' ' * (55 - len(line))}{Colors.CYAN}│{Colors.ENDC}")
            
            print(f"{Colors.CYAN}└──────────────────────────────────────────────────────┘{Colors.ENDC}")
            print(f"{Colors.GREEN}✓ Received {chunk_count} chunks in {time.time() - start_time:.2f}s{Colors.ENDC}")
            
            return full_response
        else:
            print(f"{Colors.RED}✗ Error: {response.status_code} - {response.text}{Colors.ENDC}")
            return None
    except Exception as e:
        print(f"{Colors.RED}✗ Request failed: {str(e)}{Colors.ENDC}")
        return None


if __name__ == "__main__":
    async def main():
        """Test concurrent requests to the chat endpoint with improved formatting."""
        import httpx
        import uvicorn
        import sys
        
        # Configure logging
        logger.remove()
        logger.add(sys.stdout, level="INFO")
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}=============== FINANCE CHATBOT CONCURRENT TEST ==============={Colors.ENDC}")
        
        # Sample queries - Vietnamese queries preserved properly
        sample_queries = [
            "Thông tin về những biến động gần đây của tập đoàn VNM",
            "Phân tích báo cáo tài chính của FPT năm 2023",
            "Tình hình kinh doanh của Vietcombank 6 tháng đầu năm",
            "So sánh hiệu quả kinh doanh giữa các ngân hàng niêm yết",
            "Thông tin các cổ phiếu ngành công nghệ đang tăng trưởng tốt"
        ]
        
        # Create client with extended timeout
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(
            base_url="http://localhost:8010",  # Using your port 8010
            timeout=None,  # Disable timeouts globally
            limits=limits
        ) as client:
            tasks = []
            
            # Create tasks for different users - using fewer for clearer output
            num_users = 20
            for user_id in range(1, num_users + 1):
                query = sample_queries[user_id % len(sample_queries)]
                
                # First user sends multiple queries in same session
                if user_id == 1:
                    for i in range(2):
                        specific_query = f"{query} - Query #{i+1}"
                        tasks.append(simulate_user_request(client, f"1-{i+1}", specific_query, "user1_session"))
                        await asyncio.sleep(0.5)
                else:
                    tasks.append(simulate_user_request(client, user_id, query))
            
            # Run all requests concurrently
            print(f"\n{Colors.BOLD}Running {len(tasks)} concurrent requests...{Colors.ENDC}")
            results = await asyncio.gather(*tasks)
            
            # Print summary
            success_count = len([r for r in results if r is not None])
            print(f"\n{Colors.BOLD}{Colors.HEADER}=============== TEST SUMMARY ==============={Colors.ENDC}")
            print(f"{Colors.GREEN}Successful requests: {success_count}/{len(tasks)}{Colors.ENDC}")
            
            # Test clearing chat history
            try:
                print(f"\n{Colors.BOLD}Testing chat history clearing...{Colors.ENDC}")
                clear_response = await client.post("/api/v1/clear-chat?session_id=user1_session")
                if clear_response.status_code == 200:
                    result = clear_response.json()
                    print(f"{Colors.GREEN}✓ Chat history cleared: {result['message']}{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}✗ Failed to clear chat: {clear_response.status_code}{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}✗ Error clearing chat: {str(e)}{Colors.ENDC}")

    # Run the test
    asyncio.run(main())