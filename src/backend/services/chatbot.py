"""
Chatbot service for processing user queries with context from text files.
Uses Google's Gemini AI via the LLM service adapter.
"""
from __future__ import annotations

import os
from typing import Optional, Dict, Any, List
from pathlib import Path

from loguru import logger
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.vectorstores import FAISS
# from langchain.embeddings import HuggingFaceEmbeddings
# from langchain.document_loaders import TextLoader
from langchain.document_loaders import TextLoader


from backend.services.llm_service import get_llm_service, LLMService


MODEL_NAME = "gemini-2.0-flash"


class ChatbotService:
    """Service for handling chatbot interactions with context from documents."""
    
    def __init__(self, model_name: str = MODEL_NAME):
        """
        Initialize the chatbot service.
        
        Args:
            model_name: Name of the Gemini model to use
        """
        self.model_name = model_name
        self.llm_service: LLMService = get_llm_service(model_name)
        # self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = None
        self.conversation_history: List[str] = []  # Store conversation history
        logger.info(f"Initialized Chatbot service with model: {model_name}")
    
    def load_document(self, file_path: str) -> str:
        """
        Load a document and return its content as a string.
        
        Args:
            file_path: Path to the text file to load
            
        Returns:
            String containing the document content, or None if loading failed.
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
                
            # Load the document
            loader = TextLoader(file_path)
            documents = loader.load()
            
            # Extract text content
            text = "\n".join([doc.page_content for doc in documents])
            logger.info(f"Document loaded: {file_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error loading document: {str(e)}")
            return None
    
    # def get_relevant_context(self, query: str, top_k: int = 3) -> str:
    #     """
    #     Retrieve relevant context for a query from the loaded document.
        
    #     Args:
    #         query: User query
    #         top_k: Number of most relevant chunks to retrieve
            
    #     Returns:
    #         String containing relevant context
    #     """
    #     if not self.vector_store:
    #         logger.warning("No document loaded for context retrieval")
    #         return ""
            
    #     try:
    #         # Search for relevant chunks
    #         docs = self.vector_store.similarity_search(query, k=top_k)
            
    #         # Combine chunks into context
    #         context = "\n\n".join([doc.page_content for doc in docs])
    #         return context
            
    #     except Exception as e:
    #         logger.error(f"Error retrieving context: {str(e)}")
    #         return ""
    
    def get_system_instruction(self) -> str:
        """
        Get the system instruction for the chatbot.
        
        Returns:
            System instruction string
        """
        return """
        You are a helpful financial assistant that provides accurate information based on the 
        provided context. When answering:
        
        1. Only use information from the provided context
        2. If the context doesn't contain the answer, say you don't have enough information
        3. Be concise and clear in your explanations
        4. Format financial data in a readable way
        5. Do not make up information or speculate beyond what's in the context
        
        Context is provided between [CONTEXT] tags.
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
            document_content = self.load_document(file_path)
            if not document_content:
                return "Sorry, I couldn't load the document you provided."
            
            # Prepare prompt with context
            # Include only the document content in the first turn
            if not self.conversation_history:
                prompt = f"""
                [CONTEXT]
                {document_content}
                [/CONTEXT]
                
                Based on the above context, please answer the following question:
                {query}
                """
            else:
                # Subsequent turns only include the current query and conversation history
                prompt = f"""
                [CONTEXT]
                Previous conversation:
                {chr(10).join(self.conversation_history)}
                [/CONTEXT]

                Based on the previous conversation, answer the following question:
                {query}
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


def get_chatbot_service(model_name: str = MODEL_NAME) -> ChatbotService:
    """
    Get a chatbot service instance.
    
    Args:
        model_name: Name of the model to use
        
    Returns:
        Chatbot service instance
    """
    global default_chatbot_service
    
    # Create a new instance if model name differs
    if model_name != default_chatbot_service.model_name:
        return ChatbotService(model_name)
    
    return default_chatbot_service

if __name__ == "__main__":
    # Example usage:
    chatbot = get_chatbot_service()
    
    # Create a dummy text file for testing
    dummy_file_path = "/home/nghiaph/nghiaph_workspace/experiments/finance-chatbot/archived/MSH_Baocaotaichinh_Q4_2024_Congtyme_extracted_ver1.txt"
    # with open(dummy_file_path, "w") as f:
    #     f.write("This is a test document about financial analysis. The revenue was $1 million and the profit was $200,000.")
    
    # Load the document
    document_content = chatbot.load_document(dummy_file_path)
    if document_content:
        # Ask a question
        query = "What is the report about?"
        response = chatbot.process_query(query, dummy_file_path)
        print(f"Question: {query}")
        print(f"Answer: {response}")
        
        # Ask a follow-up question, testing conversation history
        query = "Who is the chairman?"
        response = chatbot.process_query(query, dummy_file_path)
        print(f"Question: {query}")
        print(f"Answer: {response}")

        # Ask another question that the document doesn't have the answer to
        query = "What is the meaning of life?"
        response = chatbot.process_query(query, dummy_file_path)
        print(f"Question: {query}")
        print(f"Answer: {response}")

        # Ask a question about the revenue, even though it wasn't in the document,
        # to see if the chatbot remembers previous dummy content
        query = "What was the revenue mentioned earlier?"
        response = chatbot.process_query(query, dummy_file_path)
        print(f"Question: {query}")
        print(f"Answer: {response}")

        # Ask another follow-up question
        query = "Summarize the key points discussed."
        response = chatbot.process_query(query, dummy_file_path)
        print(f"Question: {query}")
        print(f"Answer: {response}")
    
    else:
        print("Failed to load the test document.")
    
    # Clean up the dummy file
    # os.remove(dummy_file_path)
    pass
