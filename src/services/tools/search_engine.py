import asyncio
import aiohttp
import json
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
from src.core.config import settings
import concurrent.futures
from functools import lru_cache
import time
from typing import List, Dict, Any, Optional
import cachetools.func
import re
from loguru import logger
# Load environment variables from .env file
load_dotenv()

# Get your Google API key and Custom Search Engine ID from environment variables
GOOGLE_API_KEY = settings.SEARCH_ENGINE_API_KEY
GOOGLE_CSE_ID = settings.SEARCH_ENGINE_CSE_ID

# Constants for optimization
CONNECTION_TIMEOUT = 5  # seconds
CONTENT_TIMEOUT = 10    # seconds
MAX_CONTENT_LENGTH = 3000  # characters
CACHE_TTL = 3600  # Cache time-to-live in seconds (1 hour)
MAX_CONCURRENT_REQUESTS = 10  # Limit concurrent requests
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Shared aiohttp session for connection pooling
_session = None

async def get_session():
    """Get or create a shared aiohttp session for connection pooling."""
    global _session
    if _session is None or _session.closed:
        conn = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS, ssl=False)
        _session = aiohttp.ClientSession(connector=conn)
    return _session

@cachetools.func.ttl_cache(maxsize=100, ttl=CACHE_TTL)
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
        'num': min(num_results, 10)  # Ensure we don't exceed API limits
    }
    
    try:
        # Use the shared session
        session = await get_session()
        async with session.get(url, params=params, timeout=CONNECTION_TIMEOUT) as response:
            if response.status != 200:
                return []
            
            # Parse the response
            results = await response.json()
            
            # Check if there are search results
            if 'items' not in results:
                return []
            
            # Extract relevant information from search results
            search_results = []
            for item in results['items']:
                search_results.append({
                    'title': item.get('title', 'No title'),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', 'No snippet')
                })
            
            return search_results
        
    except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
        return []

async def extract_content_from_url(url: str) -> str:
    """
    Extract content from a given URL asynchronously with optimizations.
    
    Args:
        url (str): The URL to extract content from
        
    Returns:
        str: Extracted content from the webpage
    """
    # Skip URLs that are likely to be problematic
    if not url or not url.startswith(('http://', 'https://')):
        return "Invalid URL format"
    
    # Check for file types that are not HTML (images, PDFs, etc.)
    if re.search(r'\.(jpg|jpeg|png|gif|pdf|doc|docx|xls|xlsx|zip|tar)$', url, re.IGNORECASE):
        return "URL points to a non-HTML file"
    
    try:
        session = await get_session()
        async with session.get(
            url, 
            headers=REQUEST_HEADERS,
            timeout=CONTENT_TIMEOUT,
            allow_redirects=True,
            ssl=False  # Speed up by skipping SSL verification
        ) as response:
            if response.status != 200:
                return ""
            
            # Check content type to ensure it's HTML
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower():
                return ""
            
            # Get the HTML content with a streaming approach
            html_content = await response.text(errors='replace')
            
            # Use a faster parser
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script, style, and other irrelevant elements
            for element in soup(['script', 'style', 'meta', 'noscript', 'header', 'footer', 'nav']):
                element.decompose()
            
            # Extract only main content areas
            main_content = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'article', 'section', 'div.content'])
            
            # If we found specific content elements, use them; otherwise, use the whole body
            if main_content:
                text = ' '.join(element.get_text(strip=True) for element in main_content)
            else:
                text = soup.get_text(separator=' ', strip=True)
            
            # Clean up text effectively
            text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
            text = text[:MAX_CONTENT_LENGTH] + ("..." if len(text) > MAX_CONTENT_LENGTH else "")
            
            return text
        
    except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeDecodeError) as e:
        return ""
    except Exception:
        return ""

async def search_and_extract(query: str, num_results: int = 3) -> List[Dict[str, Any]]:
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
    
    # Extract content from each website concurrently with a semaphore to limit concurrency
    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def extract_with_semaphore(result):
        async with sem:
            content = await extract_content_from_url(result['url'])
            return {
                'title': result['title'],
                'url': result['url'],
                'snippet': result['snippet'],
                'content': content
            }
    
    # Create extraction tasks
    tasks = [extract_with_semaphore(result) for result in search_results]
    
    # Wait for all extraction tasks to complete with timeout
    results_with_content = await asyncio.gather(*tasks)
    
    # Filter out empty results
    return [r for r in results_with_content if r['content']]

# Cache the search results
@lru_cache(maxsize=50)
def _cached_search_result(query: str, num_results: int = 10) -> str:
    """Cached version of the search result to avoid redundant searches."""
    
    async def _run_complete_search():
        start_time = time.time()
        
        # Search and extract content from websites
        results = await search_and_extract(query, num_results)
        
        if not results:
            return "No results found for the given query."
        
        # Organize the extracted content into a readable format
        organized_content = []
        
        for i, result in enumerate(results, 1):
            if not result['content']:
                continue
                
            # Format each result with title, URL, and content
            result_text = f"SOURCE {i}: {result['title']}\n"
            result_text += f"URL: {result['url']}\n"
            result_text += f"SUMMARY: {result['snippet']}\n"
            result_text += f"\nCONTENT:\n{result['content']}\n"
            result_text += "-" * 80 + "\n"  # Separator between results
            
            organized_content.append(result_text)
        
        # Join all organized content into a single string
        content = "\n".join(organized_content)
        
        # Add timing information
        elapsed = time.time() - start_time
        content += f"\nSearch completed in {elapsed:.2f} seconds."
        
        return content
    
    # Execute the search in a new event loop
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run_complete_search())
        # Clean up session at the end
        if _session and not _session.closed:
            loop.run_until_complete(_session.close())
        return result
    finally:
        loop.close()

def search_information(search_query: str) -> str:
    """
    Optimized synchronous function to search for information based on a query.
    
    Args:
        search_query: The search query
        
    Returns:
        str: Organized text content from the top search results
    """
    logger.info(f"Searching for information: {search_query}")
    try:
        # Use ThreadPoolExecutor for running the async code
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_cached_search_result, search_query, 5)  # Reduce to 5 results for speed
            return future.result(timeout=30)  # Add a timeout for the entire operation
    except concurrent.futures.TimeoutError:
        return "Search timed out. Please try a more specific query."
    except Exception as e:
        return f"Error: {str(e)}"

async def main():
    """
    Main function to run the program.
    """
    # Example usage of search_information as a synchronous function
    query = "giá cổ phiếu MSH"
    result = search_information(query)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())