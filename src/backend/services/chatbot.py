"""
Chatbot service for processing user queries with context from text files.
Uses Google's Gemini AI via the LLM service adapter.
"""
from __future__ import annotations

import os
from typing import Optional, Dict, Any, List
from pathlib import Path
import uuid

from loguru import logger
from langchain.document_loaders import TextLoader

from backend.services.llm_service import get_llm_service, LLMService


MODEL_NAME = "gemini-2.0-flash"


class ChatbotService:
    """Service for handling chatbot interactions with context from documents."""
    
    def __init__(self, model_name: str = MODEL_NAME, session_id: str = None):
        """
        Initialize the chatbot service.
        
        Args:
            model_name: Name of the Gemini model to use
            session_id: Unique identifier for the chat session
        """
        self.model_name = model_name
        self.session_id = session_id or str(uuid.uuid4())
        self.llm_service: LLMService = get_llm_service(model_name)
        self.vector_store = None
        self.conversation_history: List[str] = []  # Store conversation history
        self.current_document_path = None
        self.current_document_content = None
        logger.info(f"Initialized Chatbot service with model: {model_name}, session: {self.session_id}")
    
    def load_document(self, file_path: str) -> str:
        """
        Load a document and return its content as a string.
        
        Args:
            file_path: Path to the file to load
            
        Returns:
            String containing the document content, or None if loading failed.
        """
        if file_path is None:
            return None
            
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
                
            # Determine file type and use appropriate loader
            file_ext = os.path.splitext(file_path)[1].lower()
            # process only txt and .md files
            if file_ext == '.txt' or file_ext == '.md':
                # Load text file
                loader = TextLoader(file_path)
                documents = loader.load()
                text = "\n".join([doc.page_content for doc in documents])
            # elif file_ext == '.pdf':
            #     # Use your PDF extraction service
            #     from backend.services.data_extractor import extract_text_from_pdf
            #     text = extract_text_from_pdf(file_path)
            # else:
            #     logger.error(f"Unsupported file type: {file_ext}")
            #     return None
                
            logger.info(f"Document loaded: {file_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error loading document: {str(e)}")
            return None
    
    def get_system_instruction(self) -> str:
        """
        Get the system instruction for the chatbot.
        
        Returns:
            System instruction string
        """
        return """
        You are a helpful financial assistant that can provide information based on documents 
        or general knowledge. When answering:
        
        1. If context is provided, prioritize information from the context
        2. If the context doesn't contain the answer but you know it, provide a general answer
           based on your financial knowledge
        3. Be concise and clear in your explanations
        4. Format financial data in a readable way
        5. If you're unsure, acknowledge the limitations of your knowledge
        6. If the user asks about a topic that is not related to finance, acknowledge that you are not able to answer that question
        7. Always answer general financial questions like definitions of P/E ratio, ROI, or other common financial terms
        
        Context, when available, is provided between [CONTEXT] tags.
        """
    
    def process_query(self, query: str, file_path: Optional[str] = None) -> str:
        """
        Process a user query with context from a document.
        
        Args:
            query: User query
            file_path: Optional path to a document for context
            
        Returns:
            Response to the query
        """
        try:
            # Load document if provided
            document_content = None
            if file_path:
                # Check if we've already processed this document in this session
                if hasattr(self, 'current_document_path') and self.current_document_path == file_path:
                    logger.info(f"Using previously loaded document content for {file_path}")
                    document_content = self.current_document_content
                else:
                    document_content = self.load_document(file_path)
                    if document_content:
                        # Cache the document content and path for future queries
                        self.current_document_path = file_path
                        self.current_document_content = document_content
                        logger.info(f"Loaded and cached document content for {file_path}")
                    else:
                        return "Sorry, I couldn't load the document you provided."
            
            # Prepare prompt with context
            if document_content:
                # Include document content if available
                logger.info(f"Document content loaded, include it in the prompt")
                if not self.conversation_history:
                    prompt = f"""
                    [CONTEXT]
                    {document_content}
                    [/CONTEXT]
                    
                    Based on the above context, please answer the following question:
                    {query}
                    
                    If the context doesn't contain information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge.
                    """
                else:
                    # Subsequent turns include the current query and conversation history
                    prompt = f"""
                    [CONTEXT]
                    Previous conversation:
                    {chr(10).join(self.conversation_history)}
                    [/CONTEXT]

                    Based on the previous conversation, answer the following question:
                    {query}
                    
                    If neither the context nor the previous conversation contains information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge.
                    """
            else:
                # No document provided, just answer the question directly
                logger.info(f"No document provided, just answer the question directly")
                if not self.conversation_history:
                    prompt = f"""
                    You are a helpful financial assistant. Please answer the following question 
                    to the best of your ability:
                    {query}
                    """
                else:
                    prompt = f"""
                    [CONTEXT]
                    Previous conversation:
                    {chr(10).join(self.conversation_history)}
                    [/CONTEXT]

                    Based on the previous conversation, answer the following question:
                    {query}
                    
                    If the previous conversation doesn't contain information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge.
                    """
            
            # Generate response
            response = self.llm_service.generate_content(
                prompt=prompt,
                file_path=file_path,
                system_instruction=self.get_system_instruction()
            )
            
            if response:
                # Update conversation history
                self.conversation_history.append(f"User: {query}")
                self.conversation_history.append(f"Chatbot: {response}")
                return response
            else:
                return "Sorry, I couldn't generate a response."
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"Sorry, an error occurred while processing your query: {str(e)}"


# Create a singleton instance for easy import
default_chatbot_service = ChatbotService()

# Dictionary to store session-specific chatbot instances
chatbot_sessions = {}

def get_chatbot_service(model_name: str = MODEL_NAME, session_id: str = None) -> ChatbotService:
    """
    Get a chatbot service instance.
    
    Args:
        model_name: Name of the model to use
        session_id: Unique identifier for the chat session
        
    Returns:
        Chatbot service instance
    """
    global chatbot_sessions
    
    # Use default session if none provided
    if not session_id:
        return default_chatbot_service
    
    # Create a new session if it doesn't exist
    if session_id not in chatbot_sessions:
        chatbot_sessions[session_id] = ChatbotService(model_name, session_id)
    
    # Return existing session
    return chatbot_sessions[session_id]
