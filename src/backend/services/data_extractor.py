from loguru import logger
from google import genai
import os
import requests
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import io
from datetime import datetime

def split_pdf_to_pages(file_path: str) -> list:
    """Split PDF into individual pages"""
    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        writer = PdfWriter()
        writer.add_page(page)
        with io.BytesIO() as output_stream:
            writer.write(output_stream)
            pages.append(output_stream.getvalue())
    return pages

def merge_extracted_texts(texts: list) -> str:
    """Merge extracted texts from individual pages"""
    return "\n".join(texts)

def get_next_version(base_path: str) -> int:
    """Get next version number for extracted file"""
    version = 1
    while os.path.exists(base_path.replace('.txt', f'_v{version}.txt')):
        version += 1
    return version

def extract_text_from_pdf(file_path: str) -> str:
    client = genai.Client()
    extracted_texts = []
    timestamp = datetime.now().strftime("%Y%m%d")
    base_output_file = file_path.replace('.pdf', f'_{timestamp}_extracted.txt')
    
    # Get next version number if file exists
    version = get_next_version(base_output_file)
    output_file = base_output_file.replace('.txt', f'_v{version}.txt')
    
    try:
        # Split PDF into individual pages
        pages = split_pdf_to_pages(file_path)
        total_pages = len(pages)
        
        # Process each page separately
        for page_num, page_data in enumerate(pages, 1):
            try:
                # Create temporary file for the page
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as temp_file:
                    temp_file.write(page_data)
                    temp_file.flush()
                    
                    # Upload and process the page
                    my_file = client.files.upload(file=temp_file.name)
                    response = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=[
"""
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
""",
                            my_file
                        ]
                    )
                    
                    # Add extracted text
                    if response.text:
                        extracted_texts.append(response.text)
                    
                    # Save progress after each page
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(merge_extracted_texts(extracted_texts))
                    
                    # Log progress percentage
                    progress = (page_num / total_pages) * 100
                    logger.info(f"Progress: {progress:.1f}% ({page_num}/{total_pages} pages processed)")
                    
            except Exception as e:
                logger.error(f"Error processing page {page_num}: {e}")
                continue
        
        # Return final merged text
        return merge_extracted_texts(extracted_texts)
        
    except Exception as e:
        logger.error(f"Error processing PDF file: {e}")
        return ""

if __name__ == "__main__":
    test_file_path = "../../../data/MSH_Baocaotaichinh_Q4_2024_Congtyme.pdf"
    # test_file_path = "../../../data/arXiv 2103.15348v2.pdf"

    extracted_text = extract_text_from_pdf(test_file_path)
    timestamp = datetime.now().strftime("%Y%m%d")
    base_output_path = test_file_path.replace('.pdf', f'_{timestamp}_extracted.txt')
    version = get_next_version(base_output_path)
    output_path = base_output_path.replace('.txt', f'_v{version}.txt')
    print(f"Extracted Text saved to: {output_path}")
