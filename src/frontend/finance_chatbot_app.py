"""
Streamlit frontend for the Finance Chatbot application.
Provides a user-friendly interface for interacting with the financial assistant.
"""

import os
import streamlit as st
from pathlib import Path
import tempfile
import httpx
import asyncio
import json
from typing import Optional, Dict, Any

# Constants
UPLOAD_FOLDER = "uploads"
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Ensure upload directory exists
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

# Page configuration
st.set_page_config(
    page_title="Finance Chatbot",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def is_allowed_file(filename: str) -> bool:
    """Check if the file type is allowed."""
    allowed_extensions = {"txt", "pdf", "md", "csv", "xlsx"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

def save_uploaded_file(uploaded_file) -> str:
    """Save the uploaded file to disk and return the file path."""
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

async def upload_file_to_backend(file_path: str) -> Dict[str, Any]:
    """Upload a file to the backend for processing."""
    endpoint = f"{API_URL}/api/v1/upload-context"
    
    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                response = await client.post(endpoint, files=files)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            return {"status": "error", "message": f"Could not connect to backend: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Error uploading file: {e}"}

async def query_backend(query: str, file_path: Optional[str] = None) -> str:
    """Sends the query to the backend API asynchronously."""
    endpoint = f"{API_URL}/api/v1/chat"

    payload = {"query": query}
    if file_path:
        payload["file_path"] = file_path

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()["answer"]
        except httpx.RequestError as e:
            return f"Error: Could not connect to backend. {e}"
        except (KeyError, Exception) as e:
            return f"Error processing request: {e}"

async def upload_report(file_path: str) -> Dict[str, Any]:
    """Upload a financial report for analysis."""
    endpoint = f"{API_URL}/upload-report"
    
    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                response = await client.post(endpoint, files=files)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            return {"status": "error", "message": f"Could not connect to backend: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Error uploading report: {e}"}

def run_async(coroutine):
    """Helper function to run async functions in Streamlit."""
    return asyncio.run(coroutine)

def main():
    # App title and description
    st.title("Finance Chatbot")
    st.markdown("""
    Ask questions about financial reports and get AI-powered insights.
    Upload your financial data to analyze specific reports.
    """)
    
    # Sidebar for file upload and options
    st.sidebar.header("Upload Financial Data")
    
    # File upload options
    upload_option = st.sidebar.radio(
        "Choose upload type:",
        ["Chat Context", "Financial Report Analysis"]
    )
    
    uploaded_file = st.sidebar.file_uploader(
        "Choose a file", 
        type=["txt", "pdf", "md", "csv", "xlsx"]
    )
    
    # Initialize session state variables
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "current_file" not in st.session_state:
        st.session_state.current_file = None
        st.session_state.file_content = None
        st.session_state.analysis_result = None
    
    # Process uploaded file
    if uploaded_file is not None:
        if is_allowed_file(uploaded_file.name):
            with st.sidebar.spinner("Processing file..."):
                file_path = save_uploaded_file(uploaded_file)
                
                if upload_option == "Chat Context":
                    # Upload file for chat context
                    upload_result = run_async(upload_file_to_backend(file_path))
                    
                    if upload_result.get("status") == "success":
                        st.session_state.current_file = upload_result.get("file_path", file_path)
                        st.sidebar.success(f"File uploaded for chat context: {uploaded_file.name}")
                    else:
                        st.sidebar.error(f"Error uploading file: {upload_result.get('message', 'Unknown error')}")
                
                elif upload_option == "Financial Report Analysis":
                    # Upload file for financial analysis
                    analysis_result = run_async(upload_report(file_path))
                    
                    if "analysis" in analysis_result:
                        st.session_state.analysis_result = analysis_result["analysis"]
                        st.sidebar.success(f"Financial report analyzed: {uploaded_file.name}")
                    else:
                        st.sidebar.error(f"Error analyzing report: {analysis_result.get('message', 'Unknown error')}")
                
                # Try to read file content for preview
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        st.session_state.file_content = f.read()
                except UnicodeDecodeError:
                    st.session_state.file_content = "Binary file uploaded. Content preview not available."
                
                # Show file preview
                with st.sidebar.expander("File Preview"):
                    st.text(st.session_state.file_content[:500] + "..." if len(st.session_state.file_content or "") > 500 else st.session_state.file_content)
        else:
            st.sidebar.error(f"Invalid file type. Please upload txt, pdf, md, csv, or xlsx files.")
    
    # Create tabs for different functionalities
    tab1, tab2 = st.tabs(["Chat", "Financial Analysis"])
    
    # Chat tab
    with tab1:
        st.subheader("Chat with your Financial Data")
        
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        user_query = st.chat_input("Ask a question about your financial data...")
        
        if user_query:
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_query)
            
            # Get response from backend
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    file_path = st.session_state.current_file
                    response = run_async(query_backend(user_query, file_path))
                    st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        # Add a button to clear chat
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.experimental_rerun()
    
    # Financial Analysis tab
    with tab2:
        st.subheader("Financial Report Analysis")
        
        if st.session_state.analysis_result:
            # Display the analysis result
            st.markdown("### Analysis Results")
            
            # Check if analysis is a string or dictionary
            if isinstance(st.session_state.analysis_result, dict):
                # Display as formatted sections
                for section, content in st.session_state.analysis_result.items():
                    with st.expander(section.replace("_", " ").title()):
                        if isinstance(content, dict):
                            for key, value in content.items():
                                st.markdown(f"**{key.replace('_', ' ').title()}**: {value}")
                        else:
                            st.markdown(content)
            else:
                # Display as plain text
                st.markdown(st.session_state.analysis_result)
            
            # Add download button for analysis
            analysis_json = json.dumps(st.session_state.analysis_result, indent=2)
            st.download_button(
                label="Download Analysis",
                data=analysis_json,
                file_name="financial_analysis.json",
                mime="application/json"
            )
        else:
            st.info("Upload a financial report using the sidebar to see analysis results.")

if __name__ == "__main__":
    main() 