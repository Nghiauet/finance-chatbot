from loguru import logger
from google import genai
import os
import requests
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import io

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

def extract_text_from_pdf(file_path: str) -> str:
    client = genai.Client()
    extracted_texts = []
    
    try:
        # Split PDF into individual pages
        pages = split_pdf_to_pages(file_path)
        
        # Process each page separately
        for page_data in pages:
            # Create temporary file for the page
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as temp_file:
                temp_file.write(page_data)
                temp_file.flush()
                
                # Upload and process the page
                my_file = client.files.upload(file=temp_file.name)
                stream = client.models.generate_content_stream(
                    model='gemini-2.0-flash',
                    contents=[
                        """
                        Extract and transcribe all text content from this PDF document. Include all sections, headers, paragraphs, tables, captions, and footnotes. Maintain the original formatting and structure where possible. For any tables or numerical data, preserve the exact values and relationships. For any non-text elements like charts or images, provide a brief description of what they contain.
                        The output should be a markdown document.
                        Don't include any other text or comments.
                        Extract the content of this PDF file:
                        """,
                        my_file
                    ]
                )
                
                # Collect text from the page
                page_text = ""
                for chunk in stream:
                    if chunk.text:
                        logger.info(f"Chunk: {chunk.text}")
                        page_text += chunk.text
                
                extracted_texts.append(page_text)
        
        # Merge all extracted texts
        return merge_extracted_texts(extracted_texts)
        
    except Exception as e:
        logger.error(f"Error processing PDF file: {e}")
        return ""

if __name__ == "__main__":
    test_file_path = "/home/nghiaph/workspace/experiments/finance-chatbot/data/MSH_Baocaotaichinh_Q4_2024_Congtyme.pdf"
    extracted_text = extract_text_from_pdf(test_file_path)
    
    # Save extracted text to a file
    output_file = test_file_path.replace('.pdf', '_extracted.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(extracted_text)
    
    print(f"Extracted Text saved to: {output_file}")
