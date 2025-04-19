"""
LLM Service for interacting with Google's Gemini AI with optimized concurrency support.
"""
from __future__ import annotations

import asyncio
from typing import Optional, List, Callable, AsyncGenerator

from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, TooManyRequests
from loguru import logger

from src.core.config import llm_config
from src.core.llm_key_manager import get_key_manager


class LLMService:
    """
    Service for interacting with Google's Gemini AI models with key rotation,
    automatic retries, and model fallback capabilities.
    """
    
    # Rate limit error types that should trigger retries
    RATE_LIMIT_ERRORS = (ResourceExhausted, ServiceUnavailable, TooManyRequests)
    
    def __init__(
        self, 
        model_name: str = llm_config.default_model, 
        backup_models: Optional[List[str]] = None,
        api_key_prefix: str = "GEMINI_API_KEY",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit_duration: int = 60,
        max_concurrent_requests: int = 20
    ):
        """
        Initialize the LLM service.
        
        Args:
            model_name: Name of the Gemini model to use
            backup_models: List of backup models to use if primary model fails
            api_key_prefix: Prefix for environment variables containing API keys
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            rate_limit_duration: Duration in seconds to avoid a rate-limited key
            max_concurrent_requests: Maximum number of concurrent API requests
        """
        self.model_name = model_name
        self.backup_models = backup_models or []
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit_duration = rate_limit_duration
        self.api_key_prefix = api_key_prefix
        
        # Get the key manager for this provider
        self.key_manager = get_key_manager(api_key_prefix)
        
        # Lock for managing concurrent access to client and keys
        self.client_lock = asyncio.Lock()
        
        # Initialize client with a random key
        initial_key = self.key_manager.get_random_key()
        self.client = genai.Client(api_key=initial_key)
        self.current_key = initial_key
        
        # Semaphore for limiting concurrent API requests
        self.api_semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        logger.info(f"Initialized LLM service with model: {model_name}, max concurrent requests: {max_concurrent_requests}")
        if backup_models:
            logger.info(f"Backup models configured: {', '.join(backup_models)}")

    async def _refresh_client(self) -> str:
        """
        Get a fresh client with a different API key, with proper locking.
        
        Returns:
            The API key being used
        """
        async with self.client_lock:
            key = self.key_manager.get_random_key()
            self.client = genai.Client(api_key=key)
            self.current_key = key
            return key
        
    async def _handle_rate_limit(
        self, 
        current_key: str, 
        retry_count: int, 
        error: Exception, 
        model_index: int = 0
    ) -> tuple[int, int]:
        """
        Handle rate limit errors with retries and model fallback.
        
        Args:
            current_key: The API key that encountered a rate limit
            retry_count: Current retry attempt count
            error: The exception that was raised
            model_index: Current model index (0 = primary, 1+ = backup models)
            
        Returns:
            Tuple of (new retry count, new model index)
        """
        # Mark the current key as rate limited
        self.key_manager.mark_key_rate_limited(current_key, self.rate_limit_duration)
        
        # If we've exhausted retries with the current model, try the next model
        if retry_count >= self.max_retries:
            model_index += 1
            retry_count = 0
            
            # If we've tried all models, raise the exception
            if model_index >= len(self.backup_models) + 1:
                logger.error("All models exhausted, unable to complete request")
                raise error
                
            logger.warning(f"Switching to backup model: {self._get_model_name(model_index)}")
        else:
            # Exponential backoff
            delay = self.retry_delay * (2 ** retry_count)
            logger.info(f"Rate limit encountered. Retrying in {delay:.2f}s (attempt {retry_count+1}/{self.max_retries})")
            await asyncio.sleep(delay)
        
        return retry_count + 1, model_index
        
    def _get_model_name(self, model_index: int) -> str:
        """Get the model name based on the model index."""
        if model_index == 0:
            return self.model_name
        else:
            return self.backup_models[model_index - 1]

    async def _process_function_call_chunk(self, chunk) -> Optional[str]:
        """
        Process a chunk that might contain a function call.
        
        Args:
            chunk: Response chunk from the LLM
            
        Returns:
            Text content if available, otherwise None
        """
        # If not text, skip
        if not hasattr(chunk, 'text') or not chunk.text:
            return None
        
        # If text, return it
        return chunk.text

    async def generate_content_with_tools(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        operation_tools: Optional[List[Callable]] = None
    ) -> AsyncGenerator[Optional[str], None]:
        """
        Generate content using tools, optimized for concurrent streaming.
        
        Args:
            prompt: The text prompt to send to the model
            system_instruction: Optional system instruction for the model
            operation_tools: Optional list of callable tools
            
        Yields:
            Generated text chunks or None if generation failed
        """
        logger.info("Starting generate_content_with_tools")
        retry_count = 0
        model_index = 0
        response_stream = None
        operation_tools = operation_tools or []
        empty_chunk_count = 0
        max_empty_chunks = 3  # Maximum number of consecutive empty chunks before retrying

        # Get the stream with a semaphore - this is the only part that needs rate limiting
        while response_stream is None:
            try:
                logger.info(f"Attempting to get response stream (retry_count={retry_count}, model_index={model_index})")
                
                # Only use the semaphore for the API call, not for the entire streaming process
                async with self.api_semaphore:
                    logger.info("Acquired API semaphore")
                    
                    # Get a fresh client with a new API key for each attempt
                    current_key = await self._refresh_client()
                    
                    # Use the appropriate model based on retries
                    model_name = self._get_model_name(model_index)
                    logger.info(f"Using model: {model_name}")
                    
                    # Prepare initial content
                    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
                    
                    # Configure tools
                    config_tools = {
                        "tools": operation_tools,
                        "automatic_function_calling": {"disable": True},
                        "tool_config": {
                            "function_calling_config": {
                                "mode": "AUTO"
                            }
                        },
                        "system_instruction": system_instruction,
                        "response_mime_type": "text/plain",
                    }
                    
                    # Make initial call to get function/tool call
                    response = self.client.models.generate_content(
                        model=model_name,
                        config=config_tools,
                        contents=contents,
                    )
                    
                    # Process tool calls if present
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                await self._process_tool_call(part.function_call, operation_tools, contents)
                                
                    # Get streaming response
                    response_stream = self.client.models.generate_content_stream(
                        model=model_name,
                        config=config_tools,
                        contents=contents
                    )
                    
            except self.RATE_LIMIT_ERRORS as e:
                logger.warning(f"Rate limit error encountered: {e}")
                
                # Use semaphore for retry handling to prevent too many retries at once
                async with self.api_semaphore:
                    logger.info("Acquired API semaphore for retry handling")
                    retry_count, model_index = await self._handle_rate_limit(
                        current_key, retry_count, e, model_index
                    )
                    logger.info(f"Retry handling complete. New retry_count={retry_count}, model_index={model_index}")
                    
            except Exception as e:
                logger.error(f"Error initializing content stream with tools: {str(e)}")
                yield None
                return
        
        # Process the response stream
        try:
            logger.info("Processing response stream")
            has_yielded_content = False
            
            for chunk in response_stream:
                # Handle chunks with function calls or None text
                chunk_text = await self._process_function_call_chunk(chunk)
                
                if chunk_text is not None:
                    logger.debug(f"Received text chunk: {chunk_text}")
                    yield chunk_text
                    has_yielded_content = True
                    empty_chunk_count = 0  # Reset empty chunk counter
                else:
                    logger.debug("Received chunk with no text content")
                    empty_chunk_count += 1
                    
                    # If we've received too many empty chunks and no content yet, retry
                    if empty_chunk_count >= max_empty_chunks and not has_yielded_content:
                        logger.warning(f"Received {empty_chunk_count} empty chunks. Retrying with a new stream.")
                        # Break out of the loop to retry with a new stream
                        break
                
                await asyncio.sleep(0)  # Yield control back to event loop
            
            # If we broke out of the loop due to empty chunks and haven't yielded content, retry
            if empty_chunk_count >= max_empty_chunks and not has_yielded_content:
                logger.info("Retrying with a new stream due to empty chunks")
                # Increment retry count but stay on same model
                retry_count += 1
                
                # If we've exceeded max retries, try next model
                if retry_count >= self.max_retries:
                    model_index += 1
                    retry_count = 0
                    
                    # If we've tried all models, give up
                    if model_index >= len(self.backup_models) + 1:
                        logger.error("All models exhausted, unable to get non-empty response")
                        yield None
                        return
                
                # Recursive call to retry with new parameters
                async for text in self.generate_content_with_tools(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    operation_tools=operation_tools
                ):
                    if text is not None:
                        yield text
                
        except Exception as e:
            logger.error(f"Error processing content stream with tools: {str(e)}")
            yield None

    async def _process_tool_call(self, tool_call, operation_tools, contents):
        """Process a tool call and update contents with results."""
        logger.info(f"Tool call: {tool_call}")
        
        # Find the corresponding tool
        tool = next((t for t in operation_tools if t.__name__ == tool_call.name), None)
        if not tool:
            logger.warning(f"Tool {tool_call.name} not found in available tools.")
            return
        
        try:
            # Execute the tool
            result = await tool(**tool_call.args)
            logger.info(f"Tool {tool_call.name} results: {result}")
            
            # Create function response part
            function_response_part = types.Part.from_function_response(
                name=tool_call.name,
                response={"result": result}
            )

            # Add model's function call and function response to conversation
            contents.append(types.Content(role="model", parts=[types.Part(function_call=tool_call)]))
            contents.append(types.Content(role="user", parts=[function_response_part]))
        except Exception as e:
            logger.error(f"Error executing tool {tool_call.name}: {e}")


# Global service instance and lock
_service_lock = asyncio.Lock()
default_llm_service = None


async def get_llm_service_async(
    model_name: str = llm_config.default_model,
    backup_models: Optional[List[str]] = None,
    api_key_prefix: str = "GEMINI_API_KEY",
    force_new: bool = False
) -> LLMService:
    """
    Get an LLM service instance with proper async locking.
    
    Args:
        model_name: Name of the model to use
        backup_models: List of backup models to use if primary model fails
        api_key_prefix: Prefix for environment variables containing API keys
        force_new: Whether to force creation of a new instance
        
    Returns:
        LLM service instance
    """
    global default_llm_service
    
    # Initialize default values if None
    if backup_models is None:
        backup_models = getattr(llm_config, 'backup_models', [])
    
    async with _service_lock:
        # Create a new instance if needed
        if (default_llm_service is None or 
            force_new or 
            model_name != default_llm_service.model_name or
            backup_models != default_llm_service.backup_models or
            api_key_prefix != default_llm_service.api_key_prefix):
            
            default_llm_service = LLMService(
                model_name=model_name, 
                backup_models=backup_models,
                api_key_prefix=api_key_prefix
            )
    
    return default_llm_service