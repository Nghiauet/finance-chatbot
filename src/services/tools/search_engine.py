import asyncio
import aiohttp
import json
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
from src.core.config import settings

# Load environment variables from .env file
load_dotenv()

# Get your Google API key and Custom Search Engine ID from environment variables
GOOGLE_API_KEY = settings.SEARCH_ENGINE_API_KEY
GOOGLE_CSE_ID = settings.SEARCH_ENGINE_CSE_ID

async def search_google(query, num_results=10):
    """
    Search Google for a given query and return a list of URLs.
    
    Args:
        query (str): The search query
        num_results (int): Number of results to return (max 10 for free tier)
        
    Returns:
        list: List of dictionaries containing URL, title, and snippet
    """
    # Google Custom Search API endpoint
    url = "https://www.googleapis.com/customsearch/v1"
    
    # Parameters for the API request
    params = {
        'q': query,
        'key': GOOGLE_API_KEY,
        'cx': GOOGLE_CSE_ID,
        'num': num_results
    }
    
    try:
        # Make the API request asynchronously
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    print(f"Error: HTTP {response.status}")
                    return []
                
                # Parse the response
                results = await response.json()
                
                # Check if there are search results
                if 'items' not in results:
                    print("No results found")
                    return []
                
                # Extract relevant information from search results
                search_results = []
                for item in results['items']:
                    search_results.append({
                        'title': item['title'],
                        'url': item['link'],
                        'snippet': item['snippet']
                    })
                
                return search_results
        
    except aiohttp.ClientError as e:
        print(f"Error making API request: {e}")
        return []
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing API response: {e}")
        return []

async def extract_content_from_url(url):
    """
    Extract content from a given URL asynchronously.
    
    Args:
        url (str): The URL to extract content from
        
    Returns:
        str: Extracted content from the webpage
    """
    try:
        # Add user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Make an asynchronous request to the URL
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    return f"Error: HTTP {response.status}"
                
                # Get the HTML content
                html_content = await response.text()
                
                # Parse the HTML content
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Get text content
                text = soup.get_text(separator='\n')
                
                # Clean up text: remove extra whitespace and empty lines
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Limit the length of extracted content
                max_length = 5000
                if len(text) > max_length:
                    text = text[:max_length] + "...[content truncated]"
                
                return text
        
    except aiohttp.ClientError as e:
        return f"Error fetching content: {e}"
    except asyncio.TimeoutError:
        return "Error: Request timed out"
    except Exception as e:
        return f"Error processing content: {e}"

async def search_and_extract(query, num_results=3):
    """
    Search for websites based on a query and extract information from them asynchronously.
    
    Args:
        query (str): The search query
        num_results (int): Number of results to process
        
    Returns:
        list: List of dictionaries containing website information and extracted content
    """
    # Search for websites
    search_results = await search_google(query, num_results)
    
    if not search_results:
        return []
    
    # Extract content from each website concurrently
    tasks = []
    for result in search_results:
        print(f"Extracting content from: {result['url']}")
        task = asyncio.create_task(extract_content_from_url(result['url']))
        tasks.append((result, task))
    
    # Wait for all extraction tasks to complete
    results_with_content = []
    for result, task in tasks:
        content = await task
        results_with_content.append({
            'title': result['title'],
            'url': result['url'],
            'snippet': result['snippet'],
            'content': content
        })
    
    return results_with_content

def search_information(search_query: str) -> str:
    """
    Synchronous function to search for information based on a query.
    This function has no 'await' keywords and can be used with systems 
    that don't support asynchronous functions.
    
    Args:
        search_query: The search query
        
    Returns:
        str: Organized text content from the top search results
    """
    # Define the entire run _run_complete_search in new thread
    async def _run_complete_search():
        # Search and extract content from websites
        num_results = 10
        results = await search_and_extract(search_query, num_results)
        
        if not results:
            return "No results found for the given query."
        
        # Organize the extracted content into a readable format
        organized_content = []
        
        for i, result in enumerate(results, 1):
            # Format each result with title, URL, and content
            result_text = f"SOURCE {i}: {result['title']}\n"
            result_text += f"URL: {result['url']}\n"
            result_text += f"SUMMARY: {result['snippet']}\n"
            result_text += f"\nCONTENT:\n{result['content']}\n"
            result_text += "-" * 80 + "\n"  # Separator between results
            
            organized_content.append(result_text)
        
        # Join all organized content into a single string
        return "\n".join(organized_content)
    
    try:
        # Create a new thread with a new event loop
        import concurrent.futures
        
        # Function to run in a separate thread
        def run_in_new_thread():
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Run the search function in this new loop
            result = loop.run_until_complete(_run_complete_search())
            loop.close()
            return result
        
        # Use a ThreadPoolExecutor to run our function in a separate thread
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_new_thread)
            return future.result()
    except Exception as e:
        return f"Error: {e}"

def main():
    """
    Main function to run the program.
    """
    # Example usage of search_information as a synchronous function
    query = "giá cổ phiếu MSH"
    result = search_information(query)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())