import json
import os
import atexit
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from functools import lru_cache

from langchain_core.tools import tool
from vnstock import Vnstock

from loguru import logger

# Constants
FINANCE_DATA_CACHE_FILE = "finance_data_cache.json"
DEFAULT_CONFIG = {
    "period": "annual",
    "lang": "en",
    "dropna": True
}

# Cache management
finance_data_cache = {}

def load_finance_data_cache() -> Dict:
    """Loads finance data from the cache file."""
    logger.info(f"Loading finance data cache from {FINANCE_DATA_CACHE_FILE}")
    if not os.path.exists(FINANCE_DATA_CACHE_FILE):
        logger.warning(f"Finance data cache file {FINANCE_DATA_CACHE_FILE} does not exist. Creating a new one.")
        return {}
    try:
        with open(FINANCE_DATA_CACHE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning("Finance data cache file is corrupted. Creating a new one.")
        return {}


def save_finance_data_cache(data: Dict):
    """Saves finance data to the cache file."""
    logger.info(f"Saving finance data cache to {FINANCE_DATA_CACHE_FILE}")
    try:
        with open(FINANCE_DATA_CACHE_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving finance data cache: {e}")


def get_cached_data(data_type: str, symbol: str) -> Optional[Any]:
    """Retrieves data from the cache."""
    if symbol in finance_data_cache and data_type in finance_data_cache[symbol]:
        logger.debug(f"Returning cached {data_type} for {symbol}")
        return finance_data_cache[symbol][data_type]
    logger.debug(f"No cached {data_type} for {symbol}")
    return None


def update_cache(data_type: str, symbol: str, data: Any):
    """Updates the cache with new data."""
    if symbol not in finance_data_cache:
        finance_data_cache[symbol] = {}
    finance_data_cache[symbol][data_type] = data
    logger.debug(f"Updated cache with {data_type} for {symbol}")


# Stock client helper
def finance_client(symbol: str):
    """Returns a VnStock client for the specified symbol."""
    return Vnstock().stock(symbol=symbol, source="VCI")


# Data retrieval functions
def get_stock_price_from_vnstock(symbol: str) -> Optional[float]:
    """Get stock price using VnStock API."""
    # cached_price = get_cached_data("stock_price", symbol)
    # if cached_price:
    #     return cached_price

    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        df = Vnstock().stock(source="TCBS", symbol=symbol).quote.history(
            symbol=symbol, start=start_date, end=end_date, interval="1D"
        )
        logger.debug(f"Found price for {symbol} from TCBS")
        price = int(float(df.iloc[-1]["close"]) * 1000)
        # update_cache("stock_price", symbol, price)
        return price
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return None


def get_company_overview_from_vnstock(symbol: str) -> Optional[str]:
    """Get company overview information using VnStock API."""
    cached_overview = get_cached_data("company_overview", symbol)
    if cached_overview:
        return cached_overview

    logger.info(f"Getting company overview for {symbol}")
    try:
        overview = finance_client(symbol).company.overview()
        overview_markdown = overview.to_markdown()
        if overview_markdown is None:
            logger.error(f"Could not retrieve overview for symbol {symbol}")
            return None
        update_cache("company_overview", symbol, overview_markdown)
        return overview_markdown
    except Exception as e:
        logger.error(f"Error getting company overview for {symbol}: {e}")
        return None


def _get_financial_data(symbol: str, data_type: str, get_data_func: Callable) -> Optional[str]:
    """Generic function to get financial data using VnStock API with caching."""
    cached_data = get_cached_data(data_type, symbol)
    if cached_data:
        return cached_data

    try:
        logger.info(f"Getting {data_type} for {symbol}")
        data = get_data_func()
        if data is None:
            logger.error(f"Could not retrieve {data_type} for symbol {symbol}")
            return None
        update_cache(data_type, symbol, data)
        return data
    except Exception as e:
        logger.error(f"Error getting {data_type} for {symbol}: {e}")
        return None


def _get_financial_statement(symbol: str, statement_type: str, get_statement_func: Callable) -> Optional[str]:
    """Get financial statement with consistent formatting."""
    try:
        statement_df = get_statement_func(period=DEFAULT_CONFIG["period"])
        latest_year_data = statement_df.iloc[0]  # get the first row (latest year)
        return latest_year_data.to_markdown()
    except Exception as e:
        logger.error(f"Error processing {statement_type} for {symbol}: {e}")
        return None

def _get_financial_ratio(symbol: str, ratio_type: str, get_ratio_func: Callable) -> Optional[str]:
    """Get financial ratio with consistent formatting."""
    try:
        ratio_df = get_ratio_func(period=DEFAULT_CONFIG["period"])
        ratio_df = ratio_df.iloc[0:1]
        ratio_df_markdown = ratio_df.to_markdown()
        logger.info(f"Ratio for {symbol}: {ratio_df_markdown}")
        return ratio_df_markdown
    except Exception as e:
        logger.error(f"Error processing {ratio_type} for {symbol}: {e}")
        return None
# Public API functions
def get_current_stock_price(symbol: str) -> Optional[float]:
    """Get the current stock price of a given symbol."""
    price = get_stock_price_from_vnstock(symbol)
    logger.info(f"Get stock price for {symbol}: {price}")
    return price


def get_company_overview(symbol: str) -> Optional[str]:
    """Get the company overview of a given symbol."""
    return _get_financial_data(
        symbol, 
        "company_overview", 
        lambda: get_company_overview_from_vnstock(symbol)
    )


def get_company_balance_sheet(symbol: str) -> Optional[str]:
    """Get the company balance sheet (financial statement) of a given symbol."""
    return _get_financial_data(
        symbol,
        "balance_sheet",
        lambda: _get_financial_statement(
            symbol,
            "balance_sheet",
            lambda period: finance_client(symbol).finance.balance_sheet(period=period)
        )
    )


def get_company_income_statement(symbol: str) -> Optional[str]:
    """Get the company income statement of a given symbol."""
    return _get_financial_data(
        symbol,
        "income_statement",
        lambda: _get_financial_statement(
            symbol,
            "income_statement",
            lambda period: finance_client(symbol).finance.income_statement(period=period)
        )
    )


def get_company_cash_flow_statement(symbol: str) -> Optional[str]:
    """Get the company cash flow statement of a given symbol."""
    return _get_financial_data(
        symbol,
        "cash_flow_statement",
        lambda: _get_financial_statement(
            symbol,
            "cash_flow_statement",
            lambda period: finance_client(symbol).finance.cash_flow(period=period)
        )
    )

def get_company_ratio(symbol: str) -> Optional[str]:
    """Get the company ratio of a given symbol."""
    try:
        ratio = _get_financial_ratio(symbol, "ratio", lambda period: finance_client(symbol).finance.ratio(period=period))
        return ratio
    except Exception as e:
        logger.error(f"Error getting company ratio for {symbol}: {e}")
        return None
# Initialize and cleanup
def initialize():
    """Initialize the module by loading the cache."""
    global finance_data_cache
    finance_data_cache = load_finance_data_cache()


def on_exit():
    """Saves the finance data cache on exit."""
    save_finance_data_cache(finance_data_cache)
    logger.info("Finance data cache saved on exit.")

def get_tools():
    """Get the tools for the toolbox."""
    return [
        get_current_stock_price,
        get_company_overview,
        get_company_balance_sheet,
        get_company_income_statement,
        get_company_cash_flow_statement,
    ]
def get_stock_information(symbol: str) -> str:
    """Get the stock information for a given symbol.
    This tool will return the stock price, company overview, financial statement, income statement, and cash flow statement for a given symbol.
    Args:
        symbol: The symbol of the stock to get information for
    Returns:
        A string containing the stock information
    """
    price = get_current_stock_price(symbol)
    financial_data =f"""[STOCK INFORMATION]
    Symbol: {symbol}
    Price: {price}
    Company Overview: {get_company_overview(symbol)}
    Financial Statement: {get_company_balance_sheet(symbol)}
    Income Statement: {get_company_income_statement(symbol)}
    Cash Flow Statement: {get_company_cash_flow_statement(symbol)}
    """
    logger.info(f"return financial data for {symbol}")
    return financial_data
# Register exit handler
atexit.register(on_exit)
# Initialize module
initialize()


# Test code
if __name__ == "__main__":
    test_symbols = ["FPT"]

    logger.info("\nTesting stock data from VnStock API:")
    for symbol in test_symbols:
        try:
            price = get_current_stock_price(symbol)
            balance_sheet = get_company_balance_sheet(symbol)
            logger.info(f"{symbol} price: {price}")
            logger.info(f"{symbol} financial statement: {balance_sheet}")
            
            cash_flow_statement = get_company_cash_flow_statement(symbol)
            logger.info(f"{symbol} cash flow statement: {cash_flow_statement}")
            
            overview = get_company_overview(symbol)
            logger.info(f"{symbol} overview: {overview}")
        except Exception as e:
            logger.error(f"Error getting data for {symbol}: {e}")