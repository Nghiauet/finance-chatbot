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
from typing import List, Optional

from loguru import logger
from PyPDF2 import PdfReader, PdfWriter

from backend.services.llm_service import get_llm_service

# Constants
MODEL_NAME = "gemini-2.0-flash"
TIMESTAMP_FORMAT = "%Y%m%d"
EXTRACTION_SUFFIX = "_extracted.md"


def split_pdf_to_pages(file_path: str) -> List[bytes]:
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


def merge_extracted_texts(texts: List[str]) -> str:
    """
    Merge extracted texts from individual pages.
    
    Args:
        texts: List of extracted text strings
        
    Returns:
        Merged text with newline separators
    """
    return "\n".join(texts)


def get_next_version(base_path: str) -> int:
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


def get_extraction_prompt() -> str:
    """
    Get the prompt for Gemini AI text extraction.
    
    Returns:
        Formatted prompt string
    """
    return """
# PDF Content Extraction Instructions

Extract and convert the complete content of this PDF document following these specifications:

## Content Requirements
- Extract all text content including headers, paragraphs, footnotes, and captions
- Convert all tables to markdown format using | for columns and - for header separation
- Provide brief descriptions for non-text elements (images, charts, graphs) in [brackets]
- Maintain the original document hierarchy and section organization

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

[Begin PDF content below this line]
"""


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """
    Extract text from PDF using Google's Gemini AI.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text or None if extraction failed
    """
    llm_service = get_llm_service(MODEL_NAME)
    extracted_texts = []
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    
    # Create output file path with versioning
    base_output_file = file_path.replace('.pdf', f'_{timestamp}{EXTRACTION_SUFFIX}')
    version = get_next_version(base_output_file)
    output_file = base_output_file.replace('.txt', f'_v{version}.md')
    output_file = output_file.replace('.pdf', f'_v{version}.md')
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Split PDF into individual pages
        pages = split_pdf_to_pages(file_path)
        total_pages = len(pages)
        logger.info(f"Processing PDF with {total_pages} pages: {file_path}")
        
        # Process each page separately
        for page_num, page_data in enumerate(pages, 1):
            try:
                logger.info(f"Processing page {page_num}/{total_pages}")
                
                # Create temporary file for the page
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as temp_file:
                    temp_file.write(page_data)
                    temp_file.flush()
                    
                    # Use LLM service to process the page
                    response = llm_service.generate_content(
                        prompt=get_extraction_prompt(),
                        file_path=temp_file.name
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
                        f.write(merge_extracted_texts(extracted_texts))
                    
                    # Log progress percentage
                    progress = (page_num / total_pages) * 100
                    logger.info(f"Progress: {progress:.1f}% ({page_num}/{total_pages} pages processed)")
                    
            except Exception as e:
                logger.error(f"Error processing page {page_num}: {str(e)}")
                continue
        
        # Return final merged text
        result = merge_extracted_texts(extracted_texts)
        if not result:
            logger.warning("No text was extracted from the PDF")
            return None
        return result
        
    except Exception as e:
        logger.error(f"Error processing PDF file: {str(e)}")
        return None


if __name__ == "__main__":
    # Use Path for better path handling
    # test_file_path = str(Path(__file__).parent.parent.parent.parent / "data" / 
                        #  "3_vcs_2025_2_6_82a803b_vi_baocaotaichinhhopnhat_q4_2024_signed.pdf")
    # Alternative test file
    # test_file_path = str(Path(__file__).parent.parent.parent.parent / "data" / "arXiv 2103.15348v2.pdf")
    test_file_path = str(Path(__file__).parent.parent.parent.parent / "data" / "Pham_Hoang_Nghia_CV.pdf")

    extracted_text = extract_text_from_pdf(test_file_path)
    
    if extracted_text:
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        base_output_path = test_file_path.replace('.pdf', f'_{timestamp}{EXTRACTION_SUFFIX}')
        version = get_next_version(base_output_path) - 1
        output_path = base_output_path.replace('.txt', f'_v{version}.md')
        output_path = base_output_path.replace('.md', f'_v{version}.md')
        print(f"Extracted Text saved to: {output_path}")
    else:
        print("Text extraction failed")
