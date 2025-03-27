import json
import os
import atexit
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
import asyncio

from vnstock import Vnstock

# Constants
FINANCE_DATA_CACHE_FILE = "finance_data_cache.json"
DEFAULT_PERIOD = "annual"
finance_data_cache = {}

# Basic cache functions
def load_cache():
    """Load the finance data cache from file"""
    if not os.path.exists(FINANCE_DATA_CACHE_FILE):
        logger.warning(f"Cache file {FINANCE_DATA_CACHE_FILE} not found. Creating new cache.")
        return {}
        
    try:
        with open(FINANCE_DATA_CACHE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning("Cache file corrupted. Creating new cache.")
        return {}

def save_cache():
    """Save the finance data cache to file"""
    try:
        with open(FINANCE_DATA_CACHE_FILE, "w") as f:
            json.dump(finance_data_cache, f, indent=4)
        logger.info(f"Cache saved to {FINANCE_DATA_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")
def save_finance_data_cache(finance_data_cache):
    """Save the finance data cache to file"""
    try:
        with open(FINANCE_DATA_CACHE_FILE, "w") as f:
            json.dump(finance_data_cache, f, indent=4)
        logger.info(f"Cache saved to {FINANCE_DATA_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

# Stock data functions
async def get_stock_price(symbol):
    """Get current stock price for a symbol"""
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        
        # Use asyncio.to_thread to run this blocking operation in a thread pool
        df = await asyncio.to_thread(
            lambda: Vnstock().stock(source="TCBS", symbol=symbol).quote.history(
                symbol=symbol, start=start_date, end=end_date, interval="1D"
            )
        )
        
        price = int(float(df.iloc[-1]["close"]) * 1000)
        logger.info(f"Price for {symbol}: {price}")
        return price
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return None

def format_number(number):
    """Format large numbers for better readability"""
    if number is None:
        return "N/A"
    
    try:
        if isinstance(number, (int, float)):
            if number >= 1_000_000_000:
                return f"{number/1_000_000_000:.2f} billion"
            elif number >= 1_000_000:
                return f"{number/1_000_000:.2f} million"
            elif number >= 1_000:
                return f"{number/1_000:.2f} thousand"
            else:
                return f"{number:,}"
        return str(number)
    except:
        return str(number)

async def get_company_overview(symbol):
    """Get company overview"""
    cache_key = f"{symbol}_overview"
    
    # Check cache first
    if cache_key in finance_data_cache:
        logger.debug(f"Using cached overview for {symbol}")
        return finance_data_cache[cache_key]
    
    # Fetch fresh data
    logger.info(f"Fetching overview for {symbol}")
    try:
        # Run blocking operation in a thread pool
        client = await asyncio.to_thread(lambda: Vnstock().stock(symbol=symbol, source="VCI"))
        overview_df = await asyncio.to_thread(lambda: client.company.overview())
        
        # Format the overview data into a readable markdown
        if not overview_df.empty:
            row = overview_df.iloc[0]
            
            # Basic company information
            company_info = f"## Company Information\n"
            company_info += f"**Symbol**: {row.get('symbol', 'N/A')}\n"
            company_info += f"**Charter Capital**: {format_number(row.get('charter_capital', 0))} VND\n"
            company_info += f"**Outstanding Shares**: {format_number(row.get('issue_share', 0))}\n"
            
            # Industry classification
            industry_info = f"\n## Industry Classification\n"
            industry_info += f"**Sector**: {row.get('icb_name2', 'N/A')}\n"
            industry_info += f"**Industry Group**: {row.get('icb_name3', 'N/A')}\n"
            industry_info += f"**Sub-industry**: {row.get('icb_name4', 'N/A')}\n"
            
            # Company profile (with formatting for readability)
            profile = row.get('company_profile', '')
            if profile:
                profile_info = f"\n## Company Profile\n{profile}\n"
            else:
                profile_info = "\n## Company Profile\nNo profile available.\n"
            
            # Company history (if available)
            history = row.get('history', '')
            if history:
                history_info = f"\n## Company History\n{history}\n"
            else:
                history_info = "\n## Company History\nNo history available.\n"
            
            # Combine all sections
            overview_data = company_info + industry_info + profile_info + history_info
        else:
            overview_data = "No company overview data available."
        
        # Update cache
        finance_data_cache[cache_key] = overview_data
        
        return overview_data
    except Exception as e:
        logger.error(f"Error getting overview for {symbol}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return "Error retrieving company overview."

def format_ratio_dataframe(df):
    """Format ratio DataFrame for better readability"""
    # Create a copy to avoid modifying the original
    formatted_df = df.copy()
    
    # Reset the multi-level column index to a single level
    if isinstance(formatted_df.columns, pd.MultiIndex):
        # Extract the last level of the MultiIndex (the actual ratio name)
        new_columns = [col[-1] if isinstance(col, tuple) else col for col in formatted_df.columns]
        formatted_df.columns = new_columns
    
    # Find and rename ticker and year columns
    if '(Meta, CP)' in formatted_df.columns:
        formatted_df.rename(columns={'(Meta, CP)': 'ticker'}, inplace=True)
    if '(Meta, Năm)' in formatted_df.columns:
        formatted_df.rename(columns={'(Meta, Năm)': 'year'}, inplace=True)
    elif 'yearReport' in formatted_df.columns:
        formatted_df.rename(columns={'yearReport': 'year'}, inplace=True)
    
    # Organize columns by category
    column_categories = {
        'Valuation': ['P/B', 'P/E', 'P/S', 'P/Cash Flow', 'EPS (VND)', 'BVPS (VND)', 'EV/EBITDA', 'Vốn hóa (Tỷ đồng)', 'Số CP lưu hành (Triệu CP)'],
        'Profitability': ['Biên lợi nhuận gộp (%)', 'Biên lợi nhuận ròng (%)', 'ROE (%)', 'ROA (%)', 'ROIC (%)', 'Biên EBIT (%)', 'EBITDA (Tỷ đồng)', 'EBIT (Tỷ đồng)', 'Tỷ suất cổ tức (%)'],
        'Liquidity': ['Chỉ số thanh toán hiện thời', 'Chỉ số thanh toán tiền mặt', 'Chỉ số thanh toán nhanh', 'Khả năng chi trả lãi vay', 'Đòn bẩy tài chính'],
        'Efficiency': ['Vòng quay tài sản', 'Vòng quay TSCĐ', 'Số ngày thu tiền bình quân', 'Số ngày tồn kho bình quân', 'Số ngày thanh toán bình quân', 'Chu kỳ tiền', 'Vòng quay hàng tồn kho'],
        'Capital Structure': ['(Vay NH+DH)/VCSH', 'Nợ/VCSH', 'TSCĐ / Vốn CSH', 'Vốn CSH/Vốn điều lệ']
    }
    
    # Construct a well-organized DataFrame
    result_dict = {
        'Category': [],
        'Metric': [],
        'Value': []
    }
    
    # Start with metadata
    if 'ticker' in formatted_df.columns:
        ticker = formatted_df.iloc[0]['ticker']
    else:
        ticker = 'Unknown'
        
    if 'year' in formatted_df.columns:
        year = formatted_df.iloc[0]['year']
    else:
        year = 'Unknown'
    
    # Find all columns present in the DataFrame
    for category, metrics in column_categories.items():
        for metric in metrics:
            col_match = None
            # Try to find exact match
            if metric in formatted_df.columns:
                col_match = metric
            # Try to find partial match (for multi-level columns that might have been flattened)
            else:
                for col in formatted_df.columns:
                    if isinstance(col, str) and metric in col:
                        col_match = col
                        break
            
            if col_match is not None and not pd.isna(formatted_df.iloc[0][col_match]):
                result_dict['Category'].append(category)
                result_dict['Metric'].append(metric)
                result_dict['Value'].append(formatted_df.iloc[0][col_match])
    
    # Create a new DataFrame from our organized data
    result_df = pd.DataFrame(result_dict)
    
    # Format the markdown
    header = f"# Financial Ratios for {ticker} ({year})\n\n"
    markdown = header
    
    # Group by category and create markdown sections
    for category, group in result_df.groupby('Category'):
        markdown += f"## {category}\n\n"
        markdown += group[['Metric', 'Value']].to_markdown(index=False) + "\n\n"
    
    return markdown

async def get_financial_data(symbol, statement_type, year=None):
    """Get financial data for a specific year"""
    cache_key = f"{symbol}_{statement_type}"
    if year:
        cache_key += f"_year_{year}"
    
    # Check cache first
    if cache_key in finance_data_cache:
        logger.debug(f"Using cached data for {cache_key}")
        return finance_data_cache[cache_key]
    
    # Fetch fresh data
    logger.info(f"Fetching {statement_type} for {symbol}")
    try:
        # Run blocking operation in a thread pool
        client = await asyncio.to_thread(lambda: Vnstock().stock(symbol=symbol, source="VCI"))
        
        if statement_type == "balance_sheet":
            statement_df = await asyncio.to_thread(lambda: client.finance.balance_sheet(period=DEFAULT_PERIOD))
            year_column = 'yearReport'
        elif statement_type == "income_statement":
            statement_df = await asyncio.to_thread(lambda: client.finance.income_statement(period=DEFAULT_PERIOD))
            year_column = 'yearReport'
        elif statement_type == "cash_flow":
            statement_df = await asyncio.to_thread(lambda: client.finance.cash_flow(period=DEFAULT_PERIOD))
            year_column = 'yearReport'
        elif statement_type == "ratio":
            statement_df = await asyncio.to_thread(lambda: client.finance.ratio(period=DEFAULT_PERIOD))
            # For ratio, the year might be in '(Meta, Năm)' column based on the provided structure
            if '(Meta, Năm)' in statement_df.columns:
                year_column = '(Meta, Năm)'
            else:
                # Fallback to first column that contains 'year' or 'Năm'
                for col in statement_df.columns:
                    if isinstance(col, tuple) and ('year' in col[-1].lower() or 'năm' in col[-1].lower()):
                        year_column = col
                        break
                else:
                    year_column = 'yearReport'  # Default fallback
        else:
            return None
        
        # Process based on request type
        if year:
            # Find specific year
            if isinstance(year_column, tuple):
                # For MultiIndex columns
                year_int = int(year)
                year_rows = statement_df[statement_df[year_column] == year_int]
            else:
                # For regular columns
                year_int = int(year)
                year_rows = statement_df[statement_df[year_column] == year_int]
                
            if year_rows.empty:
                available_years = statement_df[year_column].unique().tolist()
                logger.warning(f"Year {year} not found for {symbol}. Available years: {available_years}")
                
                # Special handling for ratio DataFrame
                if statement_type == "ratio":
                    result = format_ratio_dataframe(statement_df.iloc[[0]])
                else:
                    result = statement_df.iloc[0].to_markdown()  # Default to latest
            else:
                # Special handling for ratio DataFrame
                if statement_type == "ratio":
                    result = format_ratio_dataframe(year_rows)
                else:
                    result = year_rows.iloc[0].to_markdown()
        else:
            # Default to latest year
            if statement_type == "ratio":
                result = format_ratio_dataframe(statement_df.iloc[[0]])
            else:
                result = statement_df.iloc[0].to_markdown()
        
        # Update cache
        finance_data_cache[cache_key] = result
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting {statement_type} for {symbol}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def get_balance_sheet(symbol, year=None):
    """Get balance sheet for specific year"""
    return await get_financial_data(symbol, "balance_sheet", year)

async def get_income_statement(symbol, year=None):
    """Get income statement for specific year"""
    return await get_financial_data(symbol, "income_statement", year)

async def get_cash_flow(symbol, year=None):
    """Get cash flow statement for specific year"""
    return await get_financial_data(symbol, "cash_flow", year)

async def get_financial_ratios(symbol, year=None):
    """Get financial ratios for specific year"""
    return await get_financial_data(symbol, "ratio", year)

async def get_available_years(symbol, statement_type="income_statement"):
    """Get list of available years for the given symbol"""
    try:
        # Run blocking operation in a thread pool
        client = await asyncio.to_thread(lambda: Vnstock().stock(symbol=symbol, source="VCI"))
        
        if statement_type == "balance_sheet":
            statement_df = await asyncio.to_thread(lambda: client.finance.balance_sheet(period=DEFAULT_PERIOD))
            year_column = 'yearReport'
        elif statement_type == "income_statement":
            statement_df = await asyncio.to_thread(lambda: client.finance.income_statement(period=DEFAULT_PERIOD))
            year_column = 'yearReport'
        elif statement_type == "cash_flow":
            statement_df = await asyncio.to_thread(lambda: client.finance.cash_flow(period=DEFAULT_PERIOD))
            year_column = 'yearReport'
        elif statement_type == "ratio":
            statement_df = await asyncio.to_thread(lambda: client.finance.ratio(period=DEFAULT_PERIOD))
            # For ratio, check if '(Meta, Năm)' exists
            if '(Meta, Năm)' in statement_df.columns:
                year_column = '(Meta, Năm)'
            else:
                # Try to find year column in MultiIndex columns
                for col in statement_df.columns:
                    if isinstance(col, tuple) and ('year' in col[-1].lower() or 'năm' in col[-1].lower()):
                        year_column = col
                        break
                else:
                    year_column = 'yearReport'  # Default fallback
        else:
            return []
            
        # Extract years
        years = statement_df[year_column].unique().tolist()
        return [str(year) for year in years]
        
    except Exception as e:
        logger.error(f"Error getting available years for {symbol}: {e}")
        return []

async def get_stock_information(symbol, year=None):
    """Get comprehensive stock information for a specific year"""
    price = await get_stock_price(symbol)
    overview = await get_company_overview(symbol)
    
    year_info = f" (Year: {year})" if year else " (Latest year)"
    
    # Get each statement for the specified year
    balance_sheet_md = await get_balance_sheet(symbol, year=year)
    income_md = await get_income_statement(symbol, year=year)
    cash_flow_md = await get_cash_flow(symbol, year=year)
    ratios_md = await get_financial_ratios(symbol, year=year)
    
    return f"""[STOCK INFORMATION]{year_info}
Symbol: {symbol}
Price: {price}

=== COMPANY OVERVIEW ===
{overview}

=== BALANCE SHEET ===
{balance_sheet_md}

=== INCOME STATEMENT ===
{income_md}

=== CASH FLOW STATEMENT ===
{cash_flow_md}

=== FINANCIAL RATIOS ===
{ratios_md}
"""

from typing import Optional
def get_stock_information_by_year(symbol: str, year: Optional[int] = None) -> str:
    """
    Get stock information for a specific company and year.
    Args:
        symbol: Stock ticker symbol (e.g., "FPT")
        year: Year of financial data (e.g., "2023")
    Returns:
        str: Formatted string with stock price, company overview, and financial statements 
    """
    return get_stock_information(symbol, year=year)


# Initialize and clean up
def initialize():
    global finance_data_cache
    finance_data_cache = load_cache()
    logger.info("Finance data cache loaded")

# Register exit handler to save cache
atexit.register(save_cache)

# Initialize on import
initialize()

# Test code
if __name__ == "__main__":
    test_symbols = ["FPT"]
    
    logger.info("Testing stock data retrieval:")
    for symbol in test_symbols:
        try:
            # Get available years first
            years = get_available_years(symbol)
            logger.info(f"Available years for {symbol}: {years}")
            
            # Get latest data
            latest_info = get_stock_information(symbol)
            logger.info(f"Latest information for {symbol}:\n{latest_info}")
            
            # Get data for specific year if available
            if years and len(years) > 1:
                year = years[1]  # Get second most recent year
                historical_info = get_stock_information(symbol, year=year)
                logger.info(f"Historical information for {symbol} ({year}):\n{historical_info}")
                
        except Exception as e:
            logger.error(f"Error getting data for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())