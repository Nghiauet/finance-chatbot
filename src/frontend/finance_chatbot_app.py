"""
Streamlit frontend for the Finance Chatbot application.
Provides a user-friendly interface for interacting with the financial assistant.
"""

import os
import streamlit as st
from pathlib import Path
import httpx
import asyncio
import json
from typing import Optional, Dict, Any
import uuid
import time
from loguru import logger

# Constants
UPLOAD_FOLDER = "uploads"
API_URL = os.getenv("API_URL", "http://localhost:8123")
ALLOWED_EXTENSIONS = {"txt", "pdf", "md", "csv", "xlsx"}

# Configure logger
logger.add("logs/frontend.log", rotation="10 MB", level="INFO")

# Ensure upload directory exists
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

# Page configuration
st.set_page_config(
    page_title="Finance Chatbot",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def is_allowed_file(filename: str) -> bool:
    """Check if the file type is allowed."""
    logger.debug(f"Checking file type: {filename}")
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(uploaded_file) -> str:
    """Save the uploaded file to disk and return the file path."""
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)

    logger.info(f"Saving uploaded file to: {file_path}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return file_path


async def upload_file_to_backend(file_path: str) -> Dict[str, Any]:
    """Upload a file to the backend for processing."""
    endpoint = f"{API_URL}/api/v1/upload-file"

    logger.info(f"Uploading file to backend: {file_path}")
    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                response = await client.post(endpoint, files=files, timeout=60.0)
                response.raise_for_status()
                logger.info(f"File upload successful: {file_path}")
                return response.json()
        except httpx.ConnectError:
            logger.error(f"Connection error to backend at {API_URL}")
            return {"status": "error", "message": f"Could not connect to backend at {API_URL}. Please check if the backend server is running."}
        except httpx.TimeoutException:
            logger.error(f"Timeout uploading file: {file_path}")
            return {"status": "error", "message": "Request timed out. The file may be too large or the server is busy."}
        except httpx.RequestError as e:
            logger.error(f"Request error uploading file: {e}")
            return {"status": "error", "message": f"Could not connect to backend: {e}"}
        except Exception as e:
            logger.exception(f"Unexpected error uploading file: {e}")
            return {"status": "error", "message": f"Error uploading file: {e}"}


async def query_backend(query: str, file_path: Optional[str] = None, processed_file_path: Optional[str] = None, session_id: Optional[str] = None) -> str:
    """Sends the query to the backend API asynchronously."""
    endpoint = f"{API_URL}/api/v1/chat"

    payload = {
        "query": query,
        "session_id": session_id,
    }
    if file_path:
        payload["file_path"] = file_path
    if processed_file_path:
        payload["processed_file_path"] = processed_file_path

    logger.info(f"Querying backend with session_id: {session_id}")
    logger.debug(f"Query payload: {payload}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(endpoint, json=payload, timeout=60.0)
            response.raise_for_status()
            logger.info("Query successful")
            return response.json()["answer"]
        except httpx.ConnectError:
            logger.error(f"Connection error to backend at {API_URL}")
            return f"Error: Could not connect to backend at {API_URL}. Please check if the backend server is running."
        except httpx.TimeoutException:
            logger.error("Query request timed out")
            return "Error: Request timed out. The document processing is taking longer than expected."
        except httpx.RequestError as e:
            logger.error(f"Request error during query: {e}")
            return f"Error: Request to backend failed. {str(e)}"
        except (KeyError, Exception) as e:
            logger.exception(f"Error processing query response: {e}")
            return f"Error processing request: {str(e)}"


async def upload_report(file_path: str) -> Dict[str, Any]:
    """Upload a financial report for analysis."""
    endpoint = f"{API_URL}/api/v1/upload-report"

    logger.info(f"Uploading financial report for analysis: {file_path}")
    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                response = await client.post(endpoint, files=files, timeout=120.0)
                response.raise_for_status()
                logger.info("Report upload successful")
                return response.json()
        except httpx.ConnectError:
            logger.error(f"Connection error to backend at {API_URL}")
            return {"status": "error", "message": f"Could not connect to backend at {API_URL}. Please check if the backend server is running."}
        except httpx.TimeoutException:
            logger.error(f"Timeout uploading report: {file_path}")
            return {"status": "error", "message": "Request timed out. Report analysis is taking longer than expected."}
        except httpx.RequestError as e:
            logger.error(f"Request error uploading report: {e}")
            return {"status": "error", "message": f"Could not connect to backend: {e}"}
        except Exception as e:
            logger.exception(f"Unexpected error uploading report: {e}")
            return {"status": "error", "message": f"Error uploading report: {e}"}


def run_async(coroutine):
    """Helper function to run async functions in Streamlit."""
    return asyncio.run(coroutine)


async def clear_chat_history(session_id: str) -> Dict[str, Any]:
    """Clears the chat history for a session."""
    endpoint = f"{API_URL}/api/v1/clear-chat"

    logger.info(f"Clearing chat history for session: {session_id}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(endpoint, params={"session_id": session_id})
            response.raise_for_status()
            logger.info("Chat history cleared successfully")
            return response.json()
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            return {"status": "error", "message": str(e)}


async def check_processing_status(progress_id: str) -> Dict[str, Any]:
    """Check the status of document processing."""
    endpoint = f"{API_URL}/api/v1/processing-status/{progress_id}"

    logger.debug(f"Checking processing status for ID: {progress_id}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(endpoint, timeout=10.0)
            response.raise_for_status()
            status_data = response.json()
            logger.debug(f"Processing status: {status_data.get('status')}, progress: {status_data.get('progress', 0)}%")
            return status_data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error checking status: {e.response.status_code} - {e.response.text}")
            return {
                "status": "error",
                "message": f"HTTP error: {e.response.status_code} - {e.response.text}",
                "progress": 0,
            }
        except httpx.RequestError as e:
            logger.error(f"Request error checking status: {e}")
            return {
                "status": "error",
                "message": f"Request error: {str(e)}",
                "progress": 0,
            }
        except Exception as e:
            logger.exception(f"Unexpected error checking status: {e}")
            return {
                "status": "error",
                "message": f"Error checking status: {str(e)}",
                "progress": 0,
            }


def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    logger.debug("Initializing session state")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        logger.info(f"Created new session ID: {st.session_state.session_id}")

    if "current_file" not in st.session_state:
        st.session_state.current_file = None
        st.session_state.processed_file_path = None
        st.session_state.file_content = None
        st.session_state.analysis_result = None

    if "processing_status" not in st.session_state:
        st.session_state.processing_status = None
        st.session_state.is_processing = False
        st.session_state.progress_id = None

    if "file_processed" not in st.session_state:
        st.session_state.file_processed = False

    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = {}


def handle_file_upload(uploaded_file, upload_option, status_placeholder):
    """Process the uploaded file based on the selected option."""
    logger.info(f"Handling file upload: {uploaded_file.name}, option: {upload_option}")
    if not is_allowed_file(uploaded_file.name):
        logger.warning(f"Invalid file type: {uploaded_file.name}")
        status_placeholder.error(f"Invalid file type. Please upload txt, pdf, md, csv, or xlsx files.")
        return

    # Check if this file has already been uploaded in this session
    file_key = f"{uploaded_file.name}_{upload_option}"
    if file_key in st.session_state.uploaded_files:
        logger.info(f"File already uploaded in this session: {uploaded_file.name}")
        status_placeholder.warning(f"You've already uploaded this file. Using the existing processed version.")

        # Restore the previous processing state
        previous_state = st.session_state.uploaded_files[file_key]
        st.session_state.current_file = previous_state.get("current_file")
        st.session_state.processed_file_path = previous_state.get("processed_file_path")
        st.session_state.file_processed = previous_state.get("file_processed", True)
        st.session_state.analysis_result = previous_state.get("analysis_result")
        return

    status_placeholder.info("Processing file... This may take a while for large documents.")

    file_path = save_uploaded_file(uploaded_file)

    if upload_option == "Chat Context":
        process_chat_context_file(file_path, uploaded_file.name, status_placeholder)
    elif upload_option == "Financial Report Analysis":
        process_financial_report(file_path, uploaded_file.name, status_placeholder)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            st.session_state.file_content = f.read()
            logger.debug(f"Read file content for preview: {file_path}")
    except UnicodeDecodeError:
        logger.warning(f"Binary file detected, cannot preview: {file_path}")
        st.session_state.file_content = "Binary file uploaded. Content preview not available."

    # Store the file processing state
    st.session_state.uploaded_files[file_key] = {
        "current_file": st.session_state.current_file,
        "processed_file_path": st.session_state.processed_file_path,
        "file_processed": st.session_state.file_processed,
        "analysis_result": st.session_state.analysis_result,
    }
    logger.info(f"Saved file state in session: {file_key}")


def process_chat_context_file(file_path, filename, status_placeholder):
    """Process a file uploaded for chat context."""
    logger.info(f"Processing chat context file: {filename}")

    # Check if the file has already been processed
    if st.session_state.file_processed and st.session_state.current_file == file_path:
        logger.info(f"File already processed: {filename}")
        status_placeholder.success(f"File already processed: {filename}")
        return

    with st.spinner("Uploading file to backend..."):
        upload_result = run_async(upload_file_to_backend(file_path))

    if upload_result.get("status") in ["success", "processing"]:
        st.session_state.current_file = upload_result.get("file_path", file_path)
        st.session_state.progress_id = upload_result.get("progress_id")
        logger.info(f"File uploaded successfully, progress_id: {st.session_state.progress_id}")

        if "processed_file_path" in upload_result:
            st.session_state.processed_file_path = upload_result["processed_file_path"]
            logger.info(f"Processed file path: {st.session_state.processed_file_path}")
        else:
            # For non-PDF or instant processing, use the current file as the processed file path
            st.session_state.processed_file_path = st.session_state.current_file

        if file_path.lower().endswith('.pdf'):
            logger.info("PDF file detected, starting monitoring process")
            monitor_pdf_processing(status_placeholder)
        else:
            status_placeholder.success(f"File uploaded for chat context: {filename}")
            st.session_state.file_processed = True
    else:
        error_msg = upload_result.get('message', 'Unknown error')
        logger.error(f"Error uploading file: {error_msg}")
        status_placeholder.error(f"Error uploading file: {error_msg}")


def monitor_pdf_processing(status_placeholder):
    """Monitor the progress of PDF processing."""
    logger.info("Starting PDF processing monitoring")
    st.session_state.is_processing = True
    status_placeholder.info("PDF processing started. This may take several minutes...")

    progress_bar = st.sidebar.progress(0)
    progress_text = st.sidebar.empty()

    while st.session_state.is_processing:
        status_result = run_async(check_processing_status(st.session_state.progress_id))

        if status_result.get("status") in ["completed", "success"]:
            logger.info("PDF processing completed successfully")
            progress_bar.progress(100)
            progress_text.success("Document processing completed!")
            if "processed_file_path" in status_result:
                st.session_state.processed_file_path = status_result["processed_file_path"]
                logger.info(f"Updated processed file path: {st.session_state.processed_file_path}")
            st.session_state.is_processing = False
            st.session_state.file_processed = True
            break
        elif status_result.get("status") == "processing":
            progress = status_result.get("progress", 0)
            progress_bar.progress(int(progress))
            progress_text.info(f"Processing: {progress:.1f}% complete. {status_result.get('message', '')}")
            logger.debug(f"PDF processing progress: {progress:.1f}%")
            time.sleep(5)
        elif status_result.get("status") == "error":
            error_msg = status_result.get('message', 'Unknown error')
            if "Expecting value: line 1 column 1" in error_msg:
                logger.debug("Waiting for processing to begin...")
                progress_text.info("Waiting for processing to begin...")
                time.sleep(3)
                continue
            else:
                logger.error(f"Error processing document: {error_msg}")
                progress_text.error(f"Error processing document: {error_msg}")
                st.session_state.is_processing = False
                break
        else:
            logger.debug("Waiting for status update...")
            progress_text.info("Waiting for status update...")
            time.sleep(5)


def process_financial_report(file_path, filename, status_placeholder):
    """Process a file uploaded for financial analysis."""
    logger.info(f"Processing financial report: {filename}")

    # Check if the file has already been processed
    if st.session_state.file_processed and st.session_state.current_file == file_path:
        logger.info(f"Financial report already processed: {filename}")
        status_placeholder.success(f"Financial report already processed: {filename}")
        return

    with st.spinner("Analyzing financial report..."):
        analysis_result = run_async(upload_report(file_path))

    if "analysis" in analysis_result:
        st.session_state.analysis_result = analysis_result["analysis"]
        logger.info("Financial report analysis completed successfully")
        status_placeholder.success(f"Financial report analyzed: {filename}")
        st.session_state.file_processed = True
    else:
        error_msg = analysis_result.get('message', 'Unknown error')
        logger.error(f"Error analyzing report: {error_msg}")
        status_placeholder.error(f"Error analyzing report: {error_msg}")


def display_chat_interface():
    """Display the chat interface tab."""
    logger.debug("Displaying chat interface")
    st.subheader("Chat with your Financial Data")

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_query = st.chat_input("Ask a question about your financial data...")

    if user_query:
        logger.info(f"New user query received: {user_query[:50]}...")
        st.session_state.chat_history.append({"role": "user", "content": user_query})

        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                file_path = st.session_state.current_file
                processed_file_path = st.session_state.processed_file_path

                if st.session_state.progress_id and st.session_state.processed_file_path is None:
                    logger.info("Waiting for document processing to complete before answering")
                    temp_status = st.empty()
                    temp_status.info("Waiting for document processing to complete before answering...")

                    while True:
                        status_result = run_async(check_processing_status(st.session_state.progress_id))
                        if status_result.get("status") in ["completed", "success"]:
                            if "processed_file_path" in status_result:
                                st.session_state.processed_file_path = status_result["processed_file_path"]
                                processed_file_path = status_result["processed_file_path"]
                                logger.info(f"Updated processed file path: {processed_file_path}")
                            else:
                                st.session_state.processed_file_path = file_path
                                processed_file_path = file_path
                            st.session_state.is_processing = False
                            st.session_state.file_processed = True
                            temp_status.empty()
                            break
                        time.sleep(2)

                logger.info("Sending query to backend")
                response = run_async(query_backend(
                    user_query,
                    file_path=file_path,
                    processed_file_path=processed_file_path,
                    session_id=st.session_state.session_id,
                ))
                logger.info("Response received from backend")
                st.markdown(response)

        st.session_state.chat_history.append({"role": "assistant", "content": response})
        logger.debug("Chat history updated with assistant response")

    if st.button("Clear Chat"):
        logger.info("Clear chat button clicked")
        clear_result = run_async(clear_chat_history(st.session_state.session_id))
        if clear_result.get("status") == "success":
            logger.info("Chat history cleared successfully")
            st.session_state.chat_history = []
            st.rerun()
        else:
            error_msg = clear_result.get('message', 'Unknown error')
            logger.error(f"Failed to clear chat: {error_msg}")
            st.error(f"Failed to clear chat: {error_msg}")


def display_analysis_interface():
    """Display the financial analysis tab."""
    logger.debug("Displaying analysis interface")
    st.subheader("Financial Report Analysis")

    if st.session_state.analysis_result:
        logger.debug("Displaying analysis results")
        st.markdown("### Analysis Results")

        if isinstance(st.session_state.analysis_result, dict):
            for section, content in st.session_state.analysis_result.items():
                with st.expander(section.replace("_", " ").title()):
                    if isinstance(content, dict):
                        for key, value in content.items():
                            st.markdown(f"**{key.replace('_', ' ').title()}**: {value}")
                    else:
                        st.markdown(content)
        else:
            st.markdown(st.session_state.analysis_result)

        analysis_json = json.dumps(st.session_state.analysis_result, indent=2)
        st.download_button(
            label="Download Analysis",
            data=analysis_json,
            file_name="financial_analysis.json",
            mime="application/json",
        )
    else:
        logger.debug("No analysis results to display")
        st.info("Upload a financial report using the sidebar to see analysis results.")


def main():
    logger.info("Starting Finance Chatbot application")
    st.title("Finance Chatbot")
    st.markdown("""
    Ask questions about financial reports and get AI-powered insights.
    Upload your financial data to analyze specific reports.
    """)

    initialize_session_state()

    st.sidebar.header("Upload Financial Data")

    upload_option = st.sidebar.radio(
        "Choose upload type:",
        ["Chat Context", "Financial Report Analysis"],
    )

    uploaded_file = st.sidebar.file_uploader(
        "Choose a file",
        type=list(ALLOWED_EXTENSIONS),
    )

    status_placeholder = st.sidebar.empty()

    if uploaded_file is not None:
        logger.info(f"File uploaded: {uploaded_file.name}")
        handle_file_upload(uploaded_file, upload_option, status_placeholder)

        with st.sidebar.expander("File Preview"):
            preview_content = st.session_state.file_content
            if preview_content and len(preview_content) > 500:
                preview_content = preview_content[:500] + "..."
            if uploaded_file.name.lower().endswith('.md'):
                st.markdown(preview_content)
            else:
                st.text(preview_content)

    tab1, tab2 = st.tabs(["Chat", "Financial Analysis"])

    with tab1:
        display_chat_interface()

    with tab2:
        display_analysis_interface()


def main_wrapper():
    if __name__ == "__main__":
        logger.info("Finance Chatbot application started")
        main()


main_wrapper()