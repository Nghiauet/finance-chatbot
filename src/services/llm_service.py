"""
LLM Service for interacting with Google's Gemini AI.
Provides centralized configuration and methods for text generation.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, Iterator
from pathlib import Path

from google import genai
from google.genai import types
from src.core.config import llm_config
from loguru import logger


class LLMService:
    """Service for interacting with Google's Gemini AI models."""
    
    def __init__(self, model_name: str = llm_config.default_model):
        """
        Initialize the LLM service.
        
        Args:
            model_name: Name of the Gemini model to use
        """
        self.model_name = model_name
        self.client = genai.Client(api_key=llm_config.api_key)
        logger.info(f"Initialized LLM service with model: {model_name}")

    def generate_content(
        self, 
        prompt: str, 
        file_path: Optional[str] = None, 
        generation_config: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate content using the Gemini model.
        
        Args:
            prompt: The text prompt to send to the model
            file_path: Optional path to a file to include with the prompt
            generation_config: Optional configuration parameters for generation
            system_instruction: Optional system instruction for the model
            
        Returns:
            Generated text or None if generation failed
        """
        try:
            contents = [prompt]
            
            # Add file if provided
            if file_path:
                file_obj = self.client.files.upload(file=file_path)
                contents.append(file_obj)
            
            # Create generate content config with system instruction if provided
            config = types.GenerateContentConfig()
            if system_instruction:
                config.system_instruction = system_instruction
            
            # Apply generation config if provided
            if generation_config:
                for key, value in generation_config.items():
                    setattr(config, key, value)
            
            # Generate content
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            
            return response.text if response.text else None
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            return None

    def generate_content_stream(
        self, 
        prompt: str, 
        file_path: Optional[str] = None, 
        generation_config: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None
    ) -> Iterator[Optional[str]]:
        """
        Generate content using the Gemini model with streaming.
        
        Args:
            prompt: The text prompt to send to the model.
            file_path: Optional path to a file to include with the prompt.
            generation_config: Optional configuration parameters for generation.
            system_instruction: Optional system instruction for the model.
            
        Yields:
            The generated text in chunks.
        """
        try:
            contents = [prompt]
            
            # Add file if provided
            if file_path:
                file_obj = self.client.files.upload(file=file_path)
                contents.append(file_obj)
            
            # Create generate content config with system instruction if provided
            config = types.GenerateContentConfig()
            if system_instruction:
                config.system_instruction = system_instruction
                
            # Apply generation config if provided
            if generation_config:
                for key, value in generation_config.items():
                    setattr(config, key, value)
            
            # Generate content with streaming
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config
            )
            
            for chunk in response_stream:
                yield chunk.text
                
        except Exception as e:
            logger.error(f"Error generating content stream: {str(e)}")
            yield None


# Singleton instance for easy import
default_llm_service = LLMService()


def get_llm_service(model_name: str = llm_config.default_model) -> LLMService:
    """
    Get an LLM service instance.
    
    Args:
        model_name: Name of the model to use
        
    Returns:
        LLM service instance
    """
    global default_llm_service
    
    # Create a new instance if model name differs
    if model_name != default_llm_service.model_name:
        return LLMService(model_name)
    
    return default_llm_service


if __name__ == "__main__":
    llm_service = get_llm_service()
    # Test the streaming
    prompt = "How to use the Gemini API?"
    response_stream = llm_service.generate_content_stream(prompt)
    for chunk in response_stream:
        if chunk:
            print(chunk, end="", flush=True)