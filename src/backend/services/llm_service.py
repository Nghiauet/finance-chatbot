"""
LLM Service for interacting with Google's Gemini AI.
Provides centralized configuration and methods for text generation.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from google import genai
from google.genai import types

from loguru import logger

# Constants
MODEL_NAME = "gemini-2.0-flash"


class LLMService:
    """Service for interacting with Google's Gemini AI models."""
    
    def __init__(self, model_name: str = MODEL_NAME):
        """
        Initialize the LLM service.
        
        Args:
            model_name: Name of the Gemini model to use
        """
        self.model_name = model_name
        self.client = genai.Client()
        logger.info(f"Initialized LLM service with model: {model_name}")
    
    def generate_content(self, 
                         prompt: str, 
                         file_path: Optional[str] = None, 
                         generation_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate content using the Gemini model.
        
        Args:
            prompt: The text prompt to send to the model
            file_path: Optional path to a file to include with the prompt
            generation_config: Optional configuration parameters for generation
            
        Returns:
            Generated text or None if generation failed
        """
        try:
            contents = [prompt]
            
            # Add file if provided
            if file_path:
                file_obj = self.client.files.upload(file=file_path)
                contents.append(file_obj)
            
            # Set default generation config if not provided
            if generation_config is None:
                generation_config = {
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "top_k": 40,
                }
            
            # Generate content
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
            )
            
            return response.text if response.text else None
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            return None
    
    def batch_generate(self, 
                       prompts: List[str], 
                       file_paths: Optional[List[str]] = None) -> List[Optional[str]]:
        """
        Generate content for multiple prompts.
        
        Args:
            prompts: List of text prompts
            file_paths: Optional list of file paths (must match length of prompts if provided)
            
        Returns:
            List of generated texts or None for failed generations
        """
        results = []
        
        # Validate inputs
        if file_paths and len(prompts) != len(file_paths):
            logger.error("Number of prompts must match number of file paths")
            return [None] * len(prompts)
        
        # Process each prompt
        for i, prompt in enumerate(prompts):
            file_path = file_paths[i] if file_paths else None
            result = self.generate_content(prompt, file_path)
            results.append(result)
            
        return results


# Singleton instance for easy import
default_llm_service = LLMService()


def get_llm_service(model_name: str = MODEL_NAME) -> LLMService:
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
