"""
PDF text extraction service using Google's Gemini AI.
Handles splitting PDFs into pages, extracting text, and saving results.
"""
from __future__ import annotations

import io
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import shutil
import uuid

from loguru import logger
from PyPDF2 import PdfReader, PdfWriter

from backend.services.llm_service import get_llm_service

# Constants
MODEL_NAME = "gemini-2.0-flash"
TIMESTAMP_FORMAT = "%Y%m%d"
EXTRACTION_SUFFIX = "_extracted.md"
PROGRESS_DIR = Path("data_progress")  # Directory for progress tracking files


class DataExtractor:
    """
    Class for extracting text from various file types, with focus on PDF processing.
    """
    
    def __init__(self, model_name: str = MODEL_NAME):
        """
        Initialize the DataExtractor.
        
        Args:
            model_name: Name of the LLM model to use for extraction
        """
        self.model_name = model_name
        self.processed_dir = Path("data_processed")
        self.processed_dir.mkdir(exist_ok=True, parents=True)
        # Create progress directory
        self.progress_dir = PROGRESS_DIR
        self.progress_dir.mkdir(exist_ok=True, parents=True)
    
    def split_pdf_to_pages(self, file_path: str) -> List[bytes]:
        """
        Split PDF into individual pages.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of binary page data
        """
        reader = PdfReader(file_path)
        pages = []
        
        for page in reader.pages:
            writer = PdfWriter()
            writer.add_page(page)
            with io.BytesIO() as output_stream:
                writer.write(output_stream)
                pages.append(output_stream.getvalue())
        
        return pages
    
    def merge_extracted_texts(self, texts: List[str]) -> str:
        """
        Merge extracted texts from individual pages.
        
        Args:
            texts: List of extracted text strings
            
        Returns:
            Merged text with newline separators
        """
        return "\n".join(texts)
    
    def get_next_version(self, base_path: str) -> int:
        """
        Get next version number for extracted file.
        
        Args:
            base_path: Base path for the output file
            
        Returns:
            Next version number to use
        """
        dir_path = os.path.dirname(base_path)
        base_name = os.path.basename(base_path).replace('.md', '')
        base_name = os.path.basename(base_path).replace('.txt', '')
        
        # Get all files in directory
        try:
            files = os.listdir(dir_path)
        except FileNotFoundError:
            # Directory doesn't exist, start with version 1
            return 1
        
        # Filter files that match base name pattern and extract version numbers
        versions = []
        for file in files:
            if file.startswith(base_name) and '_v' in file:
                try:
                    version_str = file.split('_v')[-1].split('.')[0]
                    version = int(version_str)
                    versions.append(version)
                except (ValueError, IndexError):
                    continue
        
        # Return next version number
        return max(versions) + 1 if versions else 1
    
    def get_extraction_system_instruction(self) -> str:
        """
        Get the system instruction for Gemini AI text extraction.
        
        Returns:
            Formatted system instruction string
        """
        return """
# PDF Content Extraction Instructions

Extract and convert the complete content of this PDF document following these specifications:

## Content Requirements
- Carefully extract all text content including headers, paragraphs, footnotes, and captions
- Convert all tables to markdown format using | for columns and - for header separation
- Provide brief descriptions for non-text elements (images, charts, graphs) in [brackets]
- Extract the original document hierarchy and section organization

## Formatting Rules
- Use ATX-style headers with a single space after # (e.g., # Heading 1)
- Add blank lines before and after headers, lists, and code blocks
- Use consistent emphasis markers: *italic* and **bold**
- Preserve all numerical values and data relationships exactly as shown
- Follow standard markdown table formatting:
  | Column 1 | Column 2 |
  |----------|----------|
  | Data     | Data     |

## Important Notes
- Convert the content exactly as presented without additional commentary
- Maintain the original document structure and flow
- Do not add explanatory text or processing notes
"""
    
    def get_extraction_prompt(self) -> str:
        """
        Get the user prompt for Gemini AI text extraction.
        
        Returns:
            Formatted user prompt string
        """
        return "Extract and convert the complete content of this PDF document to markdown format."
    
    def extract_text_from_pdf(self, file_path: str, progress_id: str = None) -> Optional[str]:
        """
        Extract text from PDF using Google's Gemini AI.
        
        Args:
            file_path: Path to the PDF file
            progress_id: ID for tracking progress
            
        Returns:
            Extracted text or None if extraction failed
        """
        llm_service = get_llm_service(self.model_name)
        extracted_texts = []
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        
        # Create progress ID if not provided
        if not progress_id:
            progress_id = str(uuid.uuid4())
        
        # Create progress file
        progress_file = self.progress_dir / f"{progress_id}.json"
        progress_data = {
            "progress_id": progress_id,
            "file_path": file_path,
            "status": "processing",
            "progress": 0,
            "message": "Starting PDF extraction",
            "timestamp": datetime.now().isoformat(),
            "processed_file_path": None
        }
        self._update_progress(progress_id, progress_data)
        
        # Create output file path with versioning directly in processed directory
        base_name = os.path.basename(file_path)
        base_name_without_ext = os.path.splitext(base_name)[0]
        base_output_file = self.processed_dir / f"{base_name_without_ext}_{timestamp}{EXTRACTION_SUFFIX}"
        version = self.get_next_version(str(base_output_file))
        output_file = str(base_output_file).replace('.txt', f'_v{version}.md')
        output_file = output_file.replace('.pdf', f'_v{version}.md')
        
        try:
            # Split PDF into individual pages
            pages = self.split_pdf_to_pages(file_path)
            total_pages = len(pages)
            logger.info(f"Processing PDF with {total_pages} pages: {file_path}")
            
            # Update progress
            progress_data.update({
                "total_pages": total_pages,
                "current_page": 0,
                "message": f"Processing PDF with {total_pages} pages"
            })
            self._update_progress(progress_id, progress_data)
            
            # Process each page separately
            for page_num, page_data in enumerate(pages, 1):
                try:
                    logger.info(f"Processing page {page_num}/{total_pages}")
                    
                    # Update progress for current page
                    progress_data.update({
                        "current_page": page_num,
                        "progress": (page_num - 1) / total_pages * 100,
                        "message": f"Processing page {page_num}/{total_pages}"
                    })
                    self._update_progress(progress_id, progress_data)
                    
                    # Create temporary file for the page
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as temp_file:
                        temp_file.write(page_data)
                        temp_file.flush()
                        
                        # Use LLM service to process the page
                        response = llm_service.generate_content(
                            prompt=self.get_extraction_prompt(),
                            file_path=temp_file.name,
                            system_instruction=self.get_extraction_system_instruction()
                        )
                        
                        # Add extracted text
                        if response:
                            # Clean response by removing markdown code block markers
                            cleaned_response = response
                            if "```markdown" in cleaned_response:
                                cleaned_response = cleaned_response.replace("```markdown", "")
                            if "```" in cleaned_response:
                                cleaned_response = cleaned_response.replace("```", "")
                            extracted_texts.append(cleaned_response)
                        else:
                            logger.warning(f"No text extracted from page {page_num}")
                        
                        # Save progress after each page
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(self.merge_extracted_texts(extracted_texts))
                        
                        # Calculate progress based on pages processed and remaining
                        progress = (page_num / total_pages) * 100
                        pages_remaining = total_pages - page_num
                        logger.info(f"Progress: {progress:.1f}% ({page_num}/{total_pages} pages processed, {pages_remaining} pages remaining)")
                        
                        # Update progress file
                        progress_data.update({
                            "progress": progress,
                            "pages_remaining": pages_remaining,
                            "message": f"Processed page {page_num}/{total_pages}",
                            "processed_file_path": output_file
                        })
                        self._update_progress(progress_id, progress_data)
                        
                except Exception as e:
                    logger.error(f"Error processing page {page_num}: {str(e)}")
                    progress_data.update({
                        "message": f"Error processing page {page_num}: {str(e)}",
                    })
                    self._update_progress(progress_id, progress_data)
                    continue
            
            # Return final merged text
            result = self.merge_extracted_texts(extracted_texts)
            if not result:
                logger.warning("No text was extracted from the PDF")
                progress_data.update({
                    "status": "error",
                    "progress": 100,
                    "message": "No text was extracted from the PDF"
                })
                self._update_progress(progress_id, progress_data)
                return None
                
            # Save the final result to the output file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            logger.info(f"Extracted text saved to: {output_file}")
            
            # Update progress file with completion status
            progress_data.update({
                "status": "completed",
                "progress": 100,
                "message": "Document processing completed",
                "processed_file_path": output_file
            })
            self._update_progress(progress_id, progress_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF file: {str(e)}")
            progress_data.update({
                "status": "error",
                "message": f"Error processing PDF file: {str(e)}"
            })
            self._update_progress(progress_id, progress_data)
            return None
    
    def _update_progress(self, progress_id: str, progress_data: Dict[str, Any]) -> None:
        """
        Update the progress file with current extraction status.
        
        Args:
            progress_id: ID of the progress file
            progress_data: Dictionary with progress information
        """
        progress_file = self.progress_dir / f"{progress_id}.json"
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error updating progress file: {str(e)}")
    
    def get_progress(self, progress_id: str) -> Dict[str, Any]:
        """
        Get the current progress of a file extraction.
        
        Args:
            progress_id: ID of the progress file
            
        Returns:
            Dictionary with progress information
        """
        logger.info(f"Getting progress for ID: {progress_id}")
        progress_file = self.progress_dir / f"{progress_id}.json"
        try:
            if progress_file.exists():
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "status": "error",
                    "progress": 0,
                    "message": f"Progress file not found for ID: {progress_id}"
                }
        except Exception as e:
            logger.error(f"Error reading progress file: {str(e)}")
            return {
                "status": "error",
                "progress": 0,
                "message": f"Error reading progress file: {str(e)}"
            }
    
    def extract_text_from_file(self, file_path: str, original_filename: str = None, progress_id: str = None) -> Dict[str, Any]:
        """
        Extract text from a file based on its type.
        
        Args:
            file_path: Path to the file
            original_filename: Original filename (useful for determining file type)
            progress_id: ID for tracking progress
            
        Returns:
            Dictionary with extraction status and file path information
        """
        try:
            # Create progress ID if not provided
            if not progress_id:
                progress_id = str(uuid.uuid4())
            
            # Determine file type from extension
            if original_filename:
                file_ext = os.path.splitext(original_filename)[1].lower()
            else:
                file_ext = os.path.splitext(file_path)[1].lower()
            
            logger.info(f"Starting text extraction for file: {file_path} (type: {file_ext})")
            
            # Initialize progress file
            progress_data = {
                "progress_id": progress_id,
                "file_path": file_path,
                "original_filename": original_filename or os.path.basename(file_path),
                "file_type": file_ext,
                "status": "processing",
                "progress": 0,
                "message": f"Starting text extraction for {file_ext} file",
                "timestamp": datetime.now().isoformat()
            }
            self._update_progress(progress_id, progress_data)
            
            # Process based on file type
            if file_ext == '.pdf':
                # For PDFs, start the extraction process
                logger.info(f"PDF detected, starting extraction process")
                
                # Extract text from PDF
                extracted_text = self.extract_text_from_pdf(file_path, progress_id)
                
                if extracted_text:
                    # Get the path to the extracted file
                    base_name = os.path.basename(file_path)
                    base_name_without_ext = os.path.splitext(base_name)[0]
                    processed_files = [f for f in os.listdir(self.processed_dir) 
                                      if f.startswith(base_name_without_ext) and 
                                      (EXTRACTION_SUFFIX in f)]
                    
                    if processed_files:
                        processed_path = str(self.processed_dir / processed_files[0])
                        result = {
                            "status": "success",
                            "message": "Text extraction completed successfully",
                            "processed_file_path": processed_path,
                            "original_file_path": file_path,
                            "progress_id": progress_id
                        }
                        # Final progress update
                        progress_data.update(result)
                        self._update_progress(progress_id, progress_data)
                        return result
                    else:
                        result = {
                            "status": "error",
                            "message": "Extracted file not found",
                            "original_file_path": file_path,
                            "progress_id": progress_id
                        }
                        progress_data.update(result)
                        self._update_progress(progress_id, progress_data)
                        return result
                else:
                    result = {
                        "status": "error",
                        "message": "Failed to extract text from PDF",
                        "original_file_path": file_path,
                        "progress_id": progress_id
                    }
                    progress_data.update(result)
                    self._update_progress(progress_id, progress_data)
                    return result
                
            elif file_ext in ['.txt', '.md']:
                # For text files, no processing needed - just copy to processed directory
                logger.info(f"Text file detected, copying to processed directory")
                
                # Update progress
                progress_data.update({
                    "progress": 50,
                    "message": "Copying text file to processed directory"
                })
                self._update_progress(progress_id, progress_data)
                
                # Copy to processed directory
                processed_filename = os.path.basename(file_path)
                processed_path = self.processed_dir / processed_filename
                shutil.copy2(file_path, processed_path)
                logger.info(f"Copied text file to processed directory: {processed_path}")
                
                # Final progress update
                result = {
                    "status": "success",
                    "message": "Text file ready for use",
                    "processed_file_path": str(processed_path),
                    "original_file_path": file_path,
                    "progress_id": progress_id,
                    "progress": 100
                }
                progress_data.update(result)
                self._update_progress(progress_id, progress_data)
                return result
                
            else:
                # For unsupported files, log a warning
                logger.warning(f"Unsupported file type for extraction: {file_ext}")
                result = {
                    "status": "error",
                    "message": f"Unsupported file type: {file_ext}",
                    "original_file_path": file_path,
                    "progress_id": progress_id
                }
                progress_data.update(result)
                self._update_progress(progress_id, progress_data)
                return result
                
        except Exception as e:
            logger.error(f"Error starting text extraction: {str(e)}")
            result = {
                "status": "error",
                "message": f"Error during extraction: {str(e)}",
                "original_file_path": file_path,
                "progress_id": progress_id if progress_id else str(uuid.uuid4())
            }
            if progress_id:
                self._update_progress(progress_id, {
                    "status": "error",
                    "message": f"Error during extraction: {str(e)}",
                    "progress": 0
                })
            return result


if __name__ == "__main__":
    # Use Path for better path handling
    test_file_path = str(Path(__file__).parent.parent.parent.parent / "data" / "Pham_Hoang_Nghia_CV.pdf")
    
    extractor = DataExtractor()
    extraction_result = extractor.extract_text_from_file(test_file_path)
    
    if extraction_result["status"] == "success":
        print(f"Extracted Text saved to: {extraction_result['processed_file_path']}")
    else:
        print(f"Text extraction failed: {extraction_result['message']}")
