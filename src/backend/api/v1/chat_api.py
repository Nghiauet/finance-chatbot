"""
Chat API endpoints for the finance chatbot.
"""
from typing import Optional, Dict, Any
import os
from pathlib import Path
import json
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Query
from pydantic import BaseModel
from loguru import logger
from PyPDF2 import PdfReader

from backend.services.chatbot import get_chatbot_service, chatbot_sessions
from backend.services.data_extractor import DataExtractor, PROGRESS_DIR

router = APIRouter()

# Define constants for file storage
UPLOAD_DIR = Path("data_uploaded")
PROCESSED_DIR = Path("data_processed")
PROGRESS_DIR = Path("data_progress")

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
PROCESSED_DIR.mkdir(exist_ok=True, parents=True)
PROGRESS_DIR.mkdir(exist_ok=True, parents=True)


class ChatQuery(BaseModel):
    """Schema for chat query requests."""
    query: str
    file_path: Optional[str] = None
    processed_file_path: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Schema for chat query responses."""
    answer: str
    metadata: Optional[Dict[str, Any]] = None


class UploadResponse(BaseModel):
    """Schema for file upload responses."""
    status: str
    message: str
    file_id: Optional[str] = None
    file_path: Optional[str] = None
    progress_id: Optional[str] = None


class ClearChatResponse(BaseModel):
    """Schema for clear chat responses."""
    status: str
    message: str


class ProcessingStatusResponse(BaseModel):
    """Schema for processing status responses."""
    status: str
    message: Optional[str] = None
    progress: Optional[float] = None
    file_path: Optional[str] = None
    processed_file_path: Optional[str] = None
    original_file_path: Optional[str] = None
    timestamp: Optional[str] = None


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
        chatbot = get_chatbot_service(session_id=query.session_id)
        # Use processed_file_path if available, otherwise use file_path
        document_path = query.processed_file_path or query.file_path
        response = chatbot.process_query(query.query, document_path)
        return ChatResponse(answer=response, metadata={"session_id": chatbot.session_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat query: {str(e)}")


@router.post("/upload-file", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Upload a file for analysis. If the file already exists, returns its processing status.
    
    Args:
        file: The file to upload
        background_tasks: FastAPI BackgroundTasks for async processing
        
    Returns:
        Dictionary with upload status and processing information
    """
    try:
        original_filename = file.filename
        
        # Check if file already exists
        existing_upload = UPLOAD_DIR / original_filename
        
        # If file already uploaded, return its status
        if existing_upload.exists():
            # Generate a new progress ID for tracking
            progress_id = str(uuid.uuid4())
            extractor = DataExtractor()
            
            # Start background task for processing with progress tracking
            background_tasks.add_task(
                extractor.extract_text_from_file,
                str(existing_upload),
                original_filename,
                progress_id
            )
            
            return UploadResponse(
                status="processing",
                message="File already exists, processing started in background",
                file_id=original_filename,
                file_path=str(existing_upload),
                progress_id=progress_id
            )
        
        # Save to upload directory
        upload_path = UPLOAD_DIR / original_filename
        
        # Save the uploaded file
        with open(upload_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Generate a progress ID for tracking
        progress_id = str(uuid.uuid4())
        
        # Start background task for processing
        extractor = DataExtractor()
        background_tasks.add_task(
            extractor.extract_text_from_file,
            str(upload_path),
            original_filename,
            progress_id
        )
        
        # Return immediate response while processing continues in background
        return UploadResponse(
            status="success",
            message="File uploaded successfully, processing started in background",
            file_id=original_filename,
            file_path=str(upload_path),
            progress_id=progress_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.post("/clear-chat", response_model=ClearChatResponse)
async def clear_chat(session_id: str = None):
    """
    Clear the conversation history for a session.
    
    Args:
        session_id: ID of the session to clear
        
    Returns:
        Status message
    """
    try:
        if session_id and session_id in chatbot_sessions:
            chatbot_sessions[session_id].conversation_history = []
            return ClearChatResponse(status="success", message="Conversation history cleared")
        return ClearChatResponse(status="error", message="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing chat history: {str(e)}")


@router.get("/processing-status/{progress_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(progress_id: str):
    """
    Get the status of document processing using a progress ID.
    
    Args:
        progress_id: ID of the progress file
        
    Returns:
        Dictionary with status and progress information
    """
    try:
        extractor = DataExtractor()
        status = extractor.get_progress(progress_id)
        return ProcessingStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error checking processing status: {str(e)}")
        return ProcessingStatusResponse(
            status="error",
            message=f"Error checking processing status: {str(e)}"
        )
