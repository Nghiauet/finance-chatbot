"""
Chatbot service for processing user queries with context from text files.
Uses Google's Gemini AI via the LLM service adapter.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.document_loaders import TextLoader
from loguru import logger
from src.services.llm_service import LLMService, get_llm_service

from src.core.config import LLMConfig

class ChatbotService:
    """Service for handling chatbot interactions with context from documents."""

    def __init__(self, model_name: str = LLMConfig.default_model, session_id: str = None):
        """
        Initialize the chatbot service.

        Args:
            model_name: Name of the Gemini model to use.
            session_id: Unique identifier for the chat session.
        """
        self.model_name = model_name
        self.session_id = session_id or str(uuid.uuid4())
        self.llm_service: LLMService = get_llm_service(model_name)
        self.vector_store = None
        self.conversation_history: List[str] = []
        self.current_document_path = None
        self.current_document_content = None
        logger.info(
            f"Initialized Chatbot service with model: {model_name}, session:"
            f" {self.session_id}"
        )

    def load_document(self, file_path: str) -> str | None:
        """
        Load a document and return its content as a string.

        Args:
            file_path: Path to the file to load.

        Returns:
            String containing the document content, or None if loading failed.
        """
        if not file_path:
            return None

        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in (".txt", ".md"):
                loader = TextLoader(file_path)
                documents = loader.load()
                text = "\n".join(doc.page_content for doc in documents)
                logger.info(f"Document loaded: {file_path}")
                return text
            else:
                logger.error(f"Unsupported file type: {file_ext}")
                return None

        except Exception as e:
            logger.error(f"Error loading document: {str(e)}")
            return None

    def get_system_instruction(self) -> str:
        """
        Get the system instruction for the chatbot.

        Returns:
            System instruction string.
        """
        return """You are a helpful financial assistant that can provide information based on documents
        or general knowledge. When answering:

        1. If context is provided, prioritize information from the context.
        2. If the context doesn't contain the answer but you know it, provide a general answer
           based on your financial knowledge.
        3. Be concise and clear in your explanations.
        4. Format financial data in a readable way.
        5. If you're unsure, acknowledge the limitations of your knowledge.
        6. If the user asks about a topic that is not related to finance, acknowledge that you are not able to answer that question.
        7. Always answer general financial questions like definitions of P/E ratio, ROI, or other common financial terms.

        Context, when available, is provided between [CONTEXT] tags."""

    def process_query(self, query: str, file_path: Optional[str] = None) -> str:
        """Process a user query with context from a document.

        Args:
            query: User query.
            file_path: Optional path to a document for context.

        Returns:
            Response to the query.
        """
        try:
            document_content = self._get_document_content(file_path)

            if document_content:
                prompt = self._build_prompt_with_context(
                    document_content, query
                )
            else:
                prompt = self._build_prompt_without_context(query)

            response = self.llm_service.generate_content(
                prompt=prompt,
                file_path=file_path,
                system_instruction=self.get_system_instruction(),
            )

            if response:
                self.conversation_history.append(f"User: {query}")
                self.conversation_history.append(f"Chatbot: {response}")
                return response
            else:
                return "Sorry, I couldn't generate a response."

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return (
                "Sorry, an error occurred while processing your query:"
                f" {str(e)}"
            )

    def _get_document_content(self, file_path: Optional[str]) -> Optional[str]:
        """Load document content from file path or retrieve from cache."""
        if not file_path:
            return None

        if (
            hasattr(self, "current_document_path")
            and self.current_document_path == file_path
        ):
            logger.info(
                "Using previously loaded document content for" f" {file_path}"
            )
            return self.current_document_content

        document_content = self.load_document(file_path)
        if document_content:
            self.current_document_path = file_path
            self.current_document_content = document_content
            logger.info(
                "Loaded and cached document content for" f" {file_path}"
            )
            return document_content
        else:
            return "Sorry, I couldn't load the document you provided."

    def _build_prompt_with_context(
        self, document_content: str, query: str
    ) -> str:
        """Build prompt string with document context."""
        context = f"""[CONTEXT]\n{document_content}\n[/CONTEXT]"""
        prompt_prefix = (
            "Based on the above context, please answer the following"
            " question:"
        )
        if self.conversation_history:
            context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(self.conversation_history)}\n[/CONTEXT]"""
            prompt_prefix = (
                "Based on the previous conversation, answer the"
                " following question:"
            )

        return f"""{context}\n{prompt_prefix}\n{query}\n\nIf neither the context nor the previous conversation contains information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge."""

    def _build_prompt_without_context(self, query: str) -> str:
        """Build prompt string without document context."""
        prompt_prefix = (
            "You are a helpful financial assistant. Please answer the"
            " following question to the best of your ability:"
        )
        if self.conversation_history:
            context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(self.conversation_history)}\n[/CONTEXT]"""
            prompt_prefix = (
                "Based on the previous conversation, answer the"
                " following question:"
            )
        else:
            context = ""

        return f"""{context}\n{prompt_prefix}\n{query}"""



default_chatbot_service = ChatbotService()
chatbot_sessions: Dict[str, ChatbotService] = {}


def get_chatbot_service(
    model_name: str = LLMConfig.default_model, session_id: str = None
) -> ChatbotService:
    """Get a chatbot service instance.

    Args:
        model_name: Name of the model to use.
        session_id: Unique identifier for the chat session.

    Returns:
        Chatbot service instance.
    """
    global chatbot_sessions

    if not session_id:
        return default_chatbot_service

    if session_id not in chatbot_sessions:
        chatbot_sessions[session_id] = ChatbotService(model_name, session_id)

    return chatbot_sessions[session_id]
