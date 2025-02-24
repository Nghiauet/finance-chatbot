"""
Financial Data Creator service for extracting structured financial data from text.
Parses financial text using Google's Gemini AI and converts it to structured format.
"""
from __future__ import annotations

import json
import re
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

from loguru import logger

from backend.services.llm_service import get_llm_service
from backend.config import get_logger

# Get configured logger
log = get_logger("financial_data_creator")
log.info("Logger initialized in FinancialDataCreator")

class FinancialDataCreator:
    """Service for extracting structured financial data from text."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the Financial Data Creator service.
        
        Args:
            model_name: Name of the LLM model to use
        """
        self.llm_service = get_llm_service(model_name)
        log.info(f"LLM service initialized with model: {model_name}")
        log.info(f"Financial Data Creator service initialized with model: {model_name}")
    
    def extract_financial_data(self, text: str, company_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract structured financial data from text.
        
        Args:
            text: Text content to extract financial data from
            company_code: Optional company code if known
            
        Returns:
            Dictionary with structured financial data
        """
        log.info("Starting financial data extraction")
        # Pre-process text to find scale (millions/thousands)
        scale_info = self._detect_scale(text)
        log.info(f"Scale detected: {scale_info}")
        
        # Try to extract company code from text if not provided
        if not company_code:
            detected_code = self._detect_company_code(text)
            if detected_code:
                company_code = detected_code
                log.info(f"Detected company code: {company_code}")
        
        # Handle long texts by splitting if necessary
        if len(text) > 12000:  # Gemini context window limitation
            log.info("Text length exceeds limit, processing as long text")
            financial_data = self._process_long_text(text, company_code, scale_info)
            log.info("Long text processing complete")
        else:
            # Create extraction prompt for Gemini
            prompt = self._create_extraction_prompt(text, company_code, scale_info)
            log.info("Extraction prompt created")
            
            # Use Gemini to extract structured data
            response = self.llm_service.generate_content(
                prompt=prompt,
                system_instruction=self._get_system_instruction()
            )
            log.info("LLM content generation complete")
            
            if not response:
                log.error("Failed to extract financial data")
                return {}
            
            # Parse the JSON response
            financial_data = self._parse_financial_data(response)
            log.info("Financial data parsing complete")
        
        # Clean and normalize the extracted data
        cleaned_data = self._clean_financial_data(financial_data, scale_info)
        log.info("Financial data cleaning complete")
        
        # Validate the data
        validated_data = self._validate_financial_data(cleaned_data, company_code)
        log.info("Financial data validation complete")
        return validated_data
    
    def _detect_company_code(self, text: str) -> Optional[str]:
        """
        Try to extract company code from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected company code or None
        """
        log.info("Attempting to detect company code")
        # Common patterns for stock symbols or company codes
        patterns = [
            r'Company Code:?\s*([A-Z0-9]{2,5})',
            r'Stock Symbol:?\s*([A-Z0-9]{2,5})',
            r'Ticker:?\s*([A-Z0-9]{2,5})',
            r'\b([A-Z0-9]{3}):?\s*[A-Z\s]+STOCK EXCHANGE\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                code = match.group(1)
                log.info(f"Company code detected using regex: {code}")
                return code
        
        # Ask LLM to identify the company code
        try:
            prompt = f"""
            Identify the company code (stock symbol/ticker) mentioned in this financial report text.
            Return ONLY the company code without any explanation.
            
            Text excerpt:
            ```
            {text[:5000]}
            ```
            """
            
            response = self.llm_service.generate_content(
                prompt=prompt,
                system_instruction="You are tasked with identifying company codes/stock symbols in financial texts. Return only the code without explanation."
            )
            log.info("LLM used to detect company code")
            
            if response:
                # Clean the response to get just the code
                code = response.strip()
                # Validate that it looks like a company code (2-5 alphanumeric characters)
                if re.match(r'^[A-Z0-9]{2,5}$', code):
                    log.info(f"Company code detected using LLM: {code}")
                    return code
            
        except Exception as e:
            log.error(f"Error detecting company code using LLM: {str(e)}")
        
        log.info("Company code detection complete (None found)")
        return None
    
    def _detect_scale(self, text: str) -> str:
        """
        Detect whether values are in thousands or millions.
        
        Args:
            text: Text to analyze
            
        Returns:
            Scale information string
        """
        log.info("Detecting scale of values")
        # Check for common phrases indicating scale
        if re.search(r'(in thousands|thousand|000\')', text, re.IGNORECASE):
            log.info("Scale detected: Thousands")
            return "Values are in thousands."
        elif re.search(r'(in millions|million|000,000\')', text, re.IGNORECASE):
            log.info("Scale detected: Millions")
            return "Values are in millions."
        else:
            log.info("Scale unclear, needs context")
            return "Scale of values (thousands/millions) is unclear. Please determine from context."
    
    def _process_long_text(self, text: str, company_code: Optional[str] = None, scale_info: str = "") -> Dict[str, Any]:
        """
        Process long text by splitting it into chunks and merging results.
        
        Args:
            text: Long text content
            company_code: Optional company code
            scale_info: Information about value scale
            
        Returns:
            Merged financial data
        """
        log.info("Processing long text by splitting into chunks")
        
        # Split text into overlapping chunks of ~10000 characters
        chunk_size = 10000
        overlap = 1000
        chunks = []
        
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
            
        log.info(f"Split text into {len(chunks)} chunks")
        
        # Process each chunk
        results = []
        for i, chunk in enumerate(chunks):
            log.info(f"Processing chunk {i+1}/{len(chunks)}")
            chunk_result = self._extract_from_chunk(chunk, company_code, scale_info)
            if chunk_result:
                results.append(chunk_result)
        
        # Merge results
        merged_data = self._merge_financial_data(results)
        log.info("Long text processing complete, data merged")
        return merged_data
    
    def _extract_from_chunk(self, text_chunk: str, company_code: Optional[str] = None, scale_info: str = "") -> Dict[str, Any]:
        """
        Extract financial data from a single text chunk.
        
        Args:
            text_chunk: Text chunk to process
            company_code: Optional company code
            scale_info: Information about value scale
            
        Returns:
            Extracted financial data
        """
        log.info("Extracting data from a chunk of text")
        prompt = self._create_extraction_prompt(text_chunk, company_code, scale_info)
        log.info("Extraction prompt created for chunk")
        
        response = self.llm_service.generate_content(
            prompt=prompt,
            system_instruction=self._get_system_instruction()
        )
        log.info("LLM content generation complete for chunk")
        
        if not response:
            log.warning("No response from LLM for chunk")
            return {}
        
        extracted_data = self._parse_financial_data(response)
        log.info("Financial data parsing complete for chunk")
        return extracted_data
    
    def _merge_financial_data(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge financial data from multiple chunks.
        
        Args:
            results: List of financial data dictionaries
            
        Returns:
            Merged financial data
        """
        log.info("Merging financial data from multiple chunks")
        if not results:
            log.warning("No results to merge")
            return {}
        
        merged_data = {}
        
        # Define priority fields (non-numeric fields that should not be merged)
        priority_fields = ['company_code', 'report_date']
        
        # First, collect all values for each field
        field_values = {}
        for result in results:
            for field, value in result.items():
                if field not in field_values:
                    field_values[field] = []
                if value is not None:
                    field_values[field].append(value)
        
        # Process each field based on type
        from collections import Counter
        for field, values in field_values.items():
            if not values:
                merged_data[field] = None
                continue
                
            if field in priority_fields:
                # For non-numeric fields, take the most frequent value
                value_counts = Counter(values)
                merged_data[field] = value_counts.most_common(1)[0][0]
                log.info(f"Merged field {field} with most common value: {merged_data[field]}")
            else:
                # For numeric fields, take the highest value (assuming they represent totals)
                try:
                    numeric_values = [float(v) for v in values if v is not None]
                    if numeric_values:
                        merged_data[field] = max(numeric_values)
                        log.info(f"Merged field {field} with max value: {merged_data[field]}")
                    else:
                        merged_data[field] = None
                except (ValueError, TypeError):
                    # If conversion fails, take the most frequent value
                    value_counts = Counter(values)
                    merged_data[field] = value_counts.most_common(1)[0][0]
                    log.info(f"Merged field {field} with most common value (after conversion failure): {merged_data[field]}")
        
        log.info(f"Merged financial data from {len(results)} chunks")
        return merged_data
    
    def _parse_financial_data(self, response: str) -> Dict[str, Any]:
        """
        Parse financial data from LLM response.
        
        Args:
            response: LLM response text
            
        Returns:
            Parsed financial data
        """
        log.info("Parsing financial data from LLM response")
        try:
            # Extract JSON from response (it might contain markdown code blocks)
            json_text = response
            
            # If response has markdown code blocks, extract the JSON
            if "```json" in response:
                json_text = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_text = response.split("```")[1].split("```")[0].strip()
            
            financial_data = json.loads(json_text)
            log.info(f"Successfully extracted financial data: {list(financial_data.keys())}")
            return financial_data
            
        except Exception as e:
            log.error(f"Error parsing financial data JSON: {str(e)}")
            log.error(f"Response: {response}")
            return {}
    
    def _create_extraction_prompt(self, text: str, company_code: Optional[str] = None, scale_info: str = "") -> str:
        """
        Create extraction prompt for the LLM.
        
        Args:
            text: Text to extract from
            company_code: Optional company code
            scale_info: Information about value scale
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""
        Extract key financial data from the following financial report text.
        
        Report text:
        ```
        {text[:10000]}
        ```
        
        {f"Company code: {company_code}" if company_code else "Please also identify the company code from the text if possible."}
        
        {scale_info}
        
        Extract the following financial metrics:
        - Company code
        - Report date (in YYYY-MM-DD format)
        - Revenue
        - Total assets
        - Current assets
        - Total liabilities
        - Current liabilities
        - Total debt
        - Net income
        
        Return the data in valid JSON format with these fields:
        {{
            "company_code": string,
            "report_date": string (YYYY-MM-DD),
            "revenue": number,
            "assets": number,
            "current_assets": number,
            "liabilities": number,
            "current_liabilities": number,
            "debt": number,
            "net_income": number
        }}
        
        If a metric is not found, set its value to null.
        Return ONLY the JSON without any explanation or additional text.
        """
        return prompt
    
    def _get_system_instruction(self) -> str:
        """
        Get system instruction for the LLM.
        
        Returns:
            System instruction string
        """
        return """
        You are a financial data extraction expert. Your task is to carefully read financial reports 
        and extract key financial metrics accurately. Be precise with numerical values and maintain 
        the correct units (thousands/millions). If a specific value is not found, use null in the JSON 
        output. If you find multiple values for the same metric (such as quarterly vs annual), 
        prioritize the most recent annual figures unless specified otherwise. Ensure the JSON output 
        is valid and complete without any explanation text before or after.
        """
    
    def _clean_financial_data(self, data: Dict[str, Any], scale_info: str) -> Dict[str, Any]:
        """
        Clean and normalize financial data.
        
        Args:
            data: Raw financial data
            scale_info: Information about value scale
            
        Returns:
            Cleaned financial data
        """
        log.info("Cleaning and normalizing financial data")
        if not data:
            log.warning("No data to clean")
            return {}
        
        # Create a copy of the data
        cleaned_data = data.copy()
        
        # Determine scale multiplier
        scale_multiplier = 1.0
        if "millions" in scale_info.lower():
            scale_multiplier = 1000000
        elif "thousands" in scale_info.lower():
            scale_multiplier = 1000
        
        # Convert numeric fields to float and apply scale
        numeric_fields = ['revenue', 'assets', 'current_assets', 'liabilities', 
                         'current_liabilities', 'debt', 'net_income']
        
        for field in numeric_fields:
            if field in cleaned_data and cleaned_data[field] is not None:
                try:
                    # Convert to float first
                    value = float(cleaned_data[field])
                    
                    # Apply scale multiplier
                    cleaned_data[field] = value * scale_multiplier
                    log.info(f"Cleaned field {field}, applied scale, new value: {cleaned_data[field]}")
                except (ValueError, TypeError):
                    # If conversion fails, set to None
                    cleaned_data[field] = None
                    log.warning(f"Failed to convert field {field} to float, set to None")
        
        # Try to parse report date
        if 'report_date' in cleaned_data and cleaned_data['report_date']:
            try:
                # Parse date and convert back to string in standard format
                date_str = cleaned_data['report_date']
                date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']
                
                for fmt in date_formats:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        cleaned_data['report_date'] = date_obj.strftime('%Y-%m-%d')
                        log.info(f"Cleaned report_date, new value: {cleaned_data['report_date']}")
                        break
                    except ValueError:
                        continue
            except Exception:
                # Keep original if parsing fails
                pass
        
        return cleaned_data
    
    def _validate_financial_data(self, data: Dict[str, Any], company_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate and ensure all required fields are present.
        
        Args:
            data: Financial data to validate
            company_code: Default company code to use if not in data
            
        Returns:
            Validated financial data
        """
        log.info("Validating financial data")
        validated_data = data.copy()
        
        # Ensure company code is set
        if not validated_data.get('company_code') and company_code:
            validated_data['company_code'] = company_code
            log.info(f"Set company_code to default: {company_code}")
        elif not validated_data.get('company_code'):
            validated_data['company_code'] = 'UNKNOWN'
            log.info("Set company_code to UNKNOWN")
        
        # Ensure report date is set
        if not validated_data.get('report_date'):
            validated_data['report_date'] = datetime.now().strftime('%Y-%m-%d')
            log.info("Set report_date to current date")
        
        # Ensure all numeric fields exist (set to None if missing)
        numeric_fields = ['revenue', 'assets', 'current_assets', 'liabilities', 
                         'current_liabilities', 'debt', 'net_income']
        
        for field in numeric_fields:
            if field not in validated_data:
                validated_data[field] = None
                log.info(f"Set missing field {field} to None")
        
        log.info(f"Validated financial data for {validated_data.get('company_code')}")
        return validated_data
    
    def extract_from_file(self, file_path: str, company_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract financial data from a file.
        
        Args:
            file_path: Path to the file
            company_code: Optional company code
            
        Returns:
            Extracted financial data
        """
        log.info(f"Extracting data from file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            log.info("File read successfully")
            
            # Derive company code from filename if not provided
            if not company_code:
                filename = os.path.basename(file_path)
                # Try to extract company code from filename
                match = re.search(r'([A-Z0-9]{2,5})', filename)
                if match:
                    company_code = match.group(1)
                    log.info(f"Derived company code from filename: {company_code}")
            
            extracted_data = self.extract_financial_data(text, company_code)
            log.info("Financial data extraction from file complete")
            return extracted_data
            
        except Exception as e:
            log.error(f"Error extracting data from file {file_path}: {str(e)}")
            return {}
    
    def create_financial_report_dict(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a dictionary suitable for creating a FinancialReport model instance.
        
        Args:
            extracted_data: Extracted financial data
            
        Returns:
            Dictionary compatible with FinancialReport model
        """
        log.info("Creating financial report dictionary")
        report_data = {
            'company_code': extracted_data.get('company_code', 'UNKNOWN'),
            'revenue': extracted_data.get('revenue'),
            'assets': extracted_data.get('assets'),
            'liabilities': extracted_data.get('liabilities'),
            'debt': extracted_data.get('debt'),
        }
        
        # Convert report_date if it exists
        if 'report_date' in extracted_data and extracted_data['report_date']:
            try:
                # If it's a string, convert to datetime
                if isinstance(extracted_data['report_date'], str):
                    report_data['report_date'] = datetime.strptime(
                        extracted_data['report_date'], '%Y-%m-%d')
                else:
                    report_data['report_date'] = extracted_data['report_date']
                log.info("Converted report_date to datetime")
            except ValueError:
                # Use current date if conversion fails
                report_data['report_date'] = datetime.now()
                log.warning("Failed to convert report_date, using current date")
        
        log.info("Financial report dictionary created")
        return report_data


# Example usage
if __name__ == "__main__":
    creator = FinancialDataCreator()
    # Test with a sample extracted markdown file
    file_name = "MSH_Baocaotaichinh_Q4_2024_Congtyme_20250224_extracted_v1.md"
    data = creator.extract_from_file(f"/home/nghiaph/nghiaph_workspace/experiments/finance-chatbot/data/{file_name}")
    # save data to a json file
    file_name = file_name.replace(".md", ".json")
    with open(f"/home/nghiaph/nghiaph_workspace/experiments/finance-chatbot/data/{file_name}", "w") as f:
        json.dump(data, f)

    from backend.services.financial_analyzer import FinancialAnalyzer
    
    analyzer = FinancialAnalyzer()
    analysis = analyzer.analyze(data)
    
    # Print the analysis
    print(analysis)
