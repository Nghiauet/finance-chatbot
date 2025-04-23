from __future__ import annotations
from typing import Dict, List, Optional, Generator, Any
import json

from openai import OpenAI
from loguru import logger


class OpenAIClient:
    """
    Client for interacting with OpenAI API with support for streaming and tools.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gemini-2.0-flash"):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key: Optional API key for OpenAI. If not provided, uses environment variable.
            base_url: Optional base URL for API endpoint. If not provided, uses default OpenAI URL.
            model: Default model to use for API calls, can be overridden in individual requests.
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        logger.debug(f"OpenAI client initialized with model {model}")
    
    def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> Any:
        """
        Generate a response from OpenAI.
        
        Args:
            prompt: The input text prompt
            model: The model to use (overrides the default if provided)
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens in the response
            tools: List of tools to use with the model
            stream: Whether to stream the response
            
        Returns:
            Either the complete response or a generator if streaming
        """
        params = {
            "model": model if model else self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
            
        if tools:
            params["tools"] = tools
            
        if stream:
            return self._stream_response(params)
        else:
            return self._complete_response(params)
    
    def _complete_response(self, params: Dict[str, Any]) -> Any:
        """
        Get a complete response from OpenAI.
        
        Args:
            params: Parameters for the API call
            
        Returns:
            The complete response or just the content depending on whether tools are used
        """
        response = self.client.chat.completions.create(**params)
        
        # If tools are being used, return the full response object
        if 'tools' in params:
            return response
        
        # Otherwise just return the content as before
        return response.choices[0].message.content
    
    def _stream_response(self, params: Dict[str, Any]) -> Generator[str, None, None]:
        """
        Stream a response from OpenAI.
        
        Args:
            params: Parameters for the API call
            
        Returns:
            Generator yielding response chunks
        """
        params["stream"] = True
        response_stream = self.client.chat.completions.create(**params)
        
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def call_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Any:
        """
        Call OpenAI with tool definitions.
        
        Args:
            prompt: The input text prompt
            tools: List of tool definitions
            model: The model to use (overrides the default if provided)
            temperature: Controls randomness (0-1)
            stream: Whether to stream the response
            
        Returns:
            Response with tool calls or a generator if streaming
        """
        return self.generate_response(
            prompt=prompt,
            model=model,
            temperature=temperature,
            tools=tools,
            stream=stream
        )

def main():
    """
    Test function to demonstrate the usage of the OpenAIClient.
    """
    import os
    from dotenv import load_dotenv
    
    # Load environment variables from .env file if present
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Optional base URL if using a proxy or custom deployment
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

    model = "gemini-2.5-flash-preview-04-17"
    
    # Initialize the client with the default model
    client = OpenAIClient(api_key=api_key, base_url=base_url, model=model)
    
    # Test with a simple prompt - no need to specify model each time
    prompt = "Tell me a short joke about programming"
    
    print(f"Sending prompt: {prompt}")
    print("\nNon-streaming response:")
    response = client.generate_response(prompt=prompt, temperature=0.7)
    print(response)
    
    print("\nStreaming response:")
    for chunk in client.generate_response(prompt=prompt, temperature=0.7, stream=True):
        print(chunk, end="", flush=True)
    print("\n")
    
    # Example with weather tool (function calling)
    weather_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    tool_prompt = "What's the weather like in San Francisco?"
    print(f"\nTesting tool calling with prompt: {tool_prompt}")
    tool_response = client.call_with_tools(prompt=tool_prompt, tools=weather_tools, temperature=0.7)
    print(json.dumps(tool_response.model_dump(), indent=2))
    
    # Example with add_numbers tool
    add_numbers_tools = [
        {
            "type": "function",
            "function": {
                "name": "add_numbers",
                "description": "Add two numbers together",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "num1": {
                            "type": "number",
                            "description": "The first number to add"
                        },
                        "num2": {
                            "type": "number",
                            "description": "The second number to add"
                        }
                    },
                    "required": ["num1", "num2"]
                }
            }
        }
    ]
    
    math_prompt = "What is the sum of 345 and 782?"
    print(f"\nTesting add_numbers tool with prompt: {math_prompt}")
    math_response = client.call_with_tools(prompt=math_prompt, tools=add_numbers_tools, temperature=0.2)
    print(json.dumps(math_response.model_dump(), indent=2))
    
    # Demonstrate how to extract and use the tool call
    if hasattr(math_response.choices[0].message, 'tool_calls') and math_response.choices[0].message.tool_calls:
        tool_call = math_response.choices[0].message.tool_calls[0]
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        print(f"\nTool call details:")
        print(f"Function name: {function_name}")
        print(f"Arguments: {function_args}")
        
        if function_name == "add_numbers":
            num1 = function_args.get("num1")
            num2 = function_args.get("num2")
            result = num1 + num2
            print(f"Calculated result: {num1} + {num2} = {result}")


if __name__ == "__main__":
    main()