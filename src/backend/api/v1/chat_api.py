"""
Chat API endpoints for the finance chatbot.
"""
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from src.backend.services.chatbot import get_chatbot_service

router = APIRouter()


class ChatQuery(BaseModel):
    """Schema for chat query requests."""
    query: str
    file_path: Optional[str] = None


class ChatResponse(BaseModel):
    """Schema for chat query responses."""
    answer: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(query: ChatQuery):
    """
    Process a chat query with optional document context.
    
    Args:
        query: ChatQuery object containing the user query and optional file path
        
    Returns:
        ChatResponse with the answer and optional metadata
    """
    try:
        chatbot = get_chatbot_service()
        response = chatbot.process_query(query.query, query.file_path)
        return ChatResponse(answer=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat query: {str(e)}")


@router.post("/upload-context", response_model=Dict[str, Any])
async def upload_context_file(file: UploadFile = File(...)):
    """
    Upload a file to use as context for chat queries.
    
    Args:
        file: The file to upload
        
    Returns:
        Dictionary with status and file path
    """
    try:
        # Create a temporary file path
        import os
        from tempfile import NamedTemporaryFile
        
        # Save the uploaded file
        with NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        return {
            "status": "success",
            "message": "File uploaded successfully",
            "file_path": temp_file_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")