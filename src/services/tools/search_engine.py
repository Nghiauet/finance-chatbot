import requests
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

def search_google(query, num_results=5):
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
        # Make the API request
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the response
        results = response.json()
        
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
        
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return []
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing API response: {e}")
        return []

def extract_content_from_url(url):
    """
    Extract content from a given URL.
    
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
        
        # Make a request to the URL
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
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
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching content: {e}"
    except Exception as e:
        return f"Error processing content: {e}"

def search_and_extract(query, num_results=3):
    """
    Search for websites based on a query and extract information from them.
    Args:
        query (str): The search query
        num_results (int): Number of results to process
        
    Returns:
        list: List of dictionaries containing website information and extracted content
    """
    # Search for websites
    search_results = search_google(query, num_results)
    
    if not search_results:
        return []
    
    # Extract content from each website
    results_with_content = []
    for result in search_results:
        print(f"Extracting content from: {result['url']}")
        content = extract_content_from_url(result['url'])
        
        results_with_content.append({
            'title': result['title'],
            'url': result['url'],
            'snippet': result['snippet'],
            'content': content
        })
    
    return results_with_content


def search_information(search_query: str) -> str:
    """
    Search for information based on a query and return organized text content from the top search results.
    Args:
        search_query: The search query        
    Returns:
        str: Organized text content from the top search results
    """
    # Search and extract content from websites
    num_results = 5
    results = search_and_extract(search_query, num_results)
    
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

def main():
    """
    Main function to run the program.
    """
    # Check if API credentials are available
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        print("Error: Google API Key and Custom Search Engine ID are required.")
        print("Please set GOOGLE_API_KEY and GOOGLE_CSE_ID in your environment variables or .env file.")
        return
    
    # Get user query
    query = "giá cổ phiếu MSH"
    num_results = 5
    # test search_information
    print(search_information(query, num_results))
    # # # Get number of results to return
    # # try:
    # #     num_results = int(input("Enter number of results to return (max 10): "))
    # #     num_results = min(10, max(1, num_results))  # Limit between 1 and 10
    # # except ValueError:
    # #     num_results = 3  # Default value
    # #     print("Invalid input. Using default value of 3.")
    
    # # Search and extract content
    # results = search_and_extract(query, num_results)
    
    # # Display results
    # if results:
    #     print("\n===== SEARCH RESULTS =====\n")
    #     for i, result in enumerate(results, 1):
    #         print(f"Result {i}:")
    #         print(f"Title: {result['title']}")
    #         print(f"URL: {result['url']}")
    #         print(f"Snippet: {result['snippet']}")
    #         print("\nExtracted Content Preview (first 300 chars):")
    #         print(f"{result['content'][:300]}...\n")
    #         print("-" * 50)
            
    #     # Option to save results to a file
    #     save_option = input("Do you want to save these results to a file? (y/n): ").lower()
    #     if save_option == 'y':
    #         filename = input("Enter filename (default: search_results.json): ") or "search_results.json"
    #         with open(filename, 'w', encoding='utf-8') as f:
    #             json.dump(results, f, ensure_ascii=False, indent=2)
    #         print(f"Results saved to {filename}")
    # else:
    #     print("No results found or error occurred during search.")

if __name__ == "__main__":
    main()