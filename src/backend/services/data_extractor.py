from loguru import logger

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts data from a PDF file using Gemini by uploading the file.

    Args:
        file_path: The path or URL to the PDF file.

    Returns:
        A string containing the extracted text content.
    """
    logger.info(f"Starting PDF extraction for file: {file_path}")
    try:
        from openai import OpenAI
        import requests
        from io import BytesIO
        logger.info("Successfully imported libraries: openai, requests, io.BytesIO")

        client = OpenAI(
            api_key= "AIzaSyAhZ1zUGaBitYjUgIK69Ac20Ya5EcR5ejw",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        logger.info("OpenAI client initialized.")

        # Determine if file_path is a URL or a local path
        if file_path.startswith("http://") or file_path.startswith("https://"):
            logger.info("File path is a URL. Downloading content.")
            response = requests.get(file_path)
            response.raise_for_status()  # Raise an exception for HTTP errors
            pdf_content = response.content
            logger.info("PDF content downloaded from URL.")
        else:
            logger.info("File path is a local path. Reading file.")
            with open(file_path, 'rb') as file:
                pdf_content = file.read()
            logger.info("PDF content read from local file.")

        logger.info("Sending request to OpenAI Gemini API for text extraction.")
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all data from this PDF file."},
                        {"type": "image_url", "image_url": {"url": "data:application/pdf;base64," + pdf_content.decode('latin-1')[:4000]}}, # Gemini API can handle base64 encoded data URLs, limiting to first 4000 chars as a placeholder. Need to check actual limit and proper way to send full PDF.
                    ],
                }
            ],
            max_tokens=1000,  # Adjust as needed for potentially larger PDF content
        )
        logger.info("Received response from OpenAI Gemini API.")

        extracted_text = response.choices[0].message.content
        logger.info("Text extracted successfully.")
        return extracted_text

    except Exception as e:
        logger.error(f"Error extracting data from PDF using OpenAI: {e}")
        return f"Error extracting data from PDF using OpenAI: {e}"

if __name__ == "__main__":
    # test_file_path = "/home/nghiaph/workspace/experiments/finance-chatbot/data/MSH_Baocaotaichinh_Q4_2024_Congtyme.pdf"  # Replace with the actual path to your test PDF file
    test_file_path = "/home/nghiaph/workspace/experiments/finance-chatbot/data/arXiv 2103.15348v2.pdf"
    extracted_text = extract_text_from_pdf(test_file_path)
    print(f"Extracted Text:\n{extracted_text}")
