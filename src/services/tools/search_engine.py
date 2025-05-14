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
# Semaphore for limiting concurrent searches
_search_semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent searches

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
                logger.warning(f"Google search API returned status {response.status} for query: {query}")
                return []
            
            # Parse the response
            results = await response.json()
            
            # Check if there are search results
            if 'items' not in results:
                logger.info(f"No search results found for query: {query}")
                return []
            
            # Extract relevant information from search results
            search_results = []
            for item in results['items']:
                search_results.append({
                    'title': item.get('title', 'No title'),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', 'No snippet')
                })
            
            logger.info(f"Found {len(search_results)} search results for query: {query}")
            return search_results
        
    except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
        logger.error(f"Error in Google search for query '{query}': {str(e)}")
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
        logger.warning(f"Invalid URL format: {url}")
        return "Invalid URL format"
    
    # Check for file types that are not HTML (images, PDFs, etc.)
    if re.search(r'\.(jpg|jpeg|png|gif|pdf|doc|docx|xls|xlsx|zip|tar)$', url, re.IGNORECASE):
        logger.warning(f"URL points to a non-HTML file: {url}")
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
                logger.warning(f"Got status {response.status} when extracting content from {url}")
                return ""
            
            # Check content type to ensure it's HTML
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower():
                logger.warning(f"Content type is not HTML: {content_type} for URL: {url}")
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
            
            logger.debug(f"Successfully extracted {len(text)} characters from {url}")
            return text
        
    except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeDecodeError) as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return ""
    except Exception as e:
        logger.exception(f"Unexpected error extracting content from {url}: {str(e)}")
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
        logger.warning(f"No search results found for query: {query}")
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
    valid_results = [r for r in results_with_content if r['content']]
    logger.info(f"Extracted content for query: {query}")
    
    return valid_results

# LRU cache for search results with a process-safe wrapper
# We'll use a dictionary as an in-memory cache
_search_cache = {}
_cache_lock = asyncio.Lock()  # Lock for thread-safe cache operations

async def search_information(search_query: str) -> str:
    """
    Fully asynchronous function to search for information based on a query.
    
    Args:
        search_query: The search query
        num_results: Number of search results to use (default 5)
        
    Returns:
        str: Organized text content from the top search results
    """
    logger.info(f"Searching for information: {search_query}")
    num_results = 10
    # Check cache first
    cache_key = f"{search_query}_{num_results}"
    async with _cache_lock:
        cached_result = _search_cache.get(cache_key)
        if cached_result:
            cache_time, result = cached_result
            # Return cached result if it's less than an hour old
            if time.time() - cache_time < CACHE_TTL:
                logger.info(f"Returning cached result for query: {search_query}")
                return result
    
    # Use a semaphore to limit concurrent searches to prevent overloading
    async with _search_semaphore:
        try:
            start_time = time.time()
            
            # Search and extract content
            results = await search_and_extract(search_query, num_results)
            
            if not results:
                no_results_msg = "No results found for the given query."
                logger.warning(f"{no_results_msg} Query: {search_query}")
                return no_results_msg
            
            # Organize the extracted content
            organized_content = []
            
            for i, result in enumerate(results, 1):
                if not result['content']:
                    continue
                    
                # Format each result
                result_text = f"SOURCE {i}: {result['title']}\n"
                result_text += f"URL: {result['url']}\n"
                result_text += f"SUMMARY: {result['snippet']}\n"
                result_text += f"\nCONTENT:\n{result['content']}\n"
                result_text += "-" * 80 + "\n"  # Separator
                
                organized_content.append(result_text)
            
            # Combine all content
            content = "\n".join(organized_content)
            
            # Add timing information
            elapsed = time.time() - start_time
            content += f"\nSearch completed in {elapsed:.2f} seconds."
            
            # Cache the result
            async with _cache_lock:
                _search_cache[cache_key] = (time.time(), content)
                
                # Clean up old cache entries if there are too many
                if len(_search_cache) > 100:
                    now = time.time()
                    # Remove oldest and expired entries
                    expired_keys = [k for k, (t, _) in _search_cache.items() if now - t > CACHE_TTL]
                    for k in expired_keys:
                        _search_cache.pop(k, None)
            
            logger.info(f"Search completed for '{search_query}' in {elapsed:.2f} seconds with {len(organized_content)} results")
            return content
            
        except asyncio.TimeoutError:
            error_msg = "Search timed out. Please try a more specific query."
            logger.error(f"{error_msg} Query: {search_query}")
            return error_msg
        except Exception as e:
            error_msg = f"Error during search: {str(e)}"
            logger.exception(f"{error_msg} Query: {search_query}")
            return error_msg

async def main():
    """
    Main function to run the program.
    """
    # Example usage of search_information as an async function
    query = "giá cổ phiếu MSH"
    result = await search_information(query)
    print(result)
    
    # Demonstrate concurrent search capability
    search_queries = [
        "giá cổ phiếu VNM",
        "tình hình kinh doanh FPT",
        "báo cáo tài chính Vietcombank"
    ]
    
    # Run multiple searches concurrently
    results = await asyncio.gather(*[search_information(q) for q in search_queries])
    
    # Print summary
    for i, (query, result) in enumerate(zip(search_queries, results), 1):
        print(f"\nResult {i} for query: {query}")
        print(f"Length: {len(result)} characters")
        print(f"Preview: {result[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())