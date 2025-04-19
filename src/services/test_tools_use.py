import asyncio
import json
from typing import Dict, Any, List

# Import the LLM service
from services.gemini_client import get_llm_service_async
from src.services.tools.search_engine import search_information
from src.services.tools.get_stock_information_tools import get_stock_information_by_year

async def test_tool_calling():
    """Test the tool calling functionality with the LLM service."""
    # Get the LLM service
    llm_service = await get_llm_service_async()
    
    # Define the prompt that should trigger tool usage
    prompt = "Lưu chuyển tiền tệ của cổ phiếu của TCB và thông tin thị trường hôm nay"
    
    # Define a system instruction to encourage tool use
    system_instruction = """You are a helpful assistant that provides stock market information.
    Use the search_information tool to check the current stock market information when asked.
    Use the get_stock_information_by_year tool to check the current stock balance sheet , cash flow statement and financial ratios of stock
    Always provide stock market information in a friendly, conversational manner."""
    
    # Map of available tools
    operation_tools = [search_information, get_stock_information_by_year]
    
    print("Sending request to Gemini with tools...")
    print(f"Prompt: {prompt}")
    print("Waiting for response...")
    
    # Store the full response
    full_response = ""
    
    # Generate and stream the response
    async for chunk in llm_service.generate_content_with_tools(
        prompt=prompt,
        system_instruction=system_instruction,
        operation_tools=operation_tools
    ):
        if chunk is None:
            print("Error: Failed to generate content")
            return
        
        # Print each chunk as it arrives
        print(chunk, end="", flush=True)
        full_response += chunk
    
    print("\n\nFull response received.")
    
    # Check if the response contains function calls
    # Note: In a real implementation, you would parse the function calls from the response
    # and execute them, then follow up with the model to complete the interaction
    if "get_weather" in full_response:
        print("\nDetected potential tool usage in the response.")
        # In a real implementation, you would parse and execute the tool calls here


async def main():
    """Main function to run the test."""
    print("Starting Gemini tools test...")
    
    try:
        await test_tool_calling()
    except Exception as e:
        print(f"Error during test: {str(e)}")
    
    print("\nTest completed.")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())