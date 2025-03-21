import json
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, Optional, Callable

from langchain_core.tools import tool
from vnstock import Vnstock

from src.core.config import logger
import os
import atexit

FINANCE_DATA_CACHE_FILE = "finance_data_cache.json"


def load_finance_data_cache() -> Dict:
    """Loads finance data from the cache file."""
    logger.info(f"Loading finance data cache from {FINANCE_DATA_CACHE_FILE}")
    # check if file exists
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


finance_data_cache = load_finance_data_cache()


def get_cached_data(data_type: str, symbol: str):
    """Retrieves data from the cache."""
    if symbol in finance_data_cache and data_type in finance_data_cache[symbol]:
        logger.debug(f"Returning cached {data_type} for {symbol}")
        return finance_data_cache[symbol][data_type]
    else:
        logger.debug(f"No cached {data_type} for {symbol}")
        return None


def update_cache(data_type: str, symbol: str, data):
    """Updates the cache with new data."""
    if symbol not in finance_data_cache:
        finance_data_cache[symbol] = {}
    finance_data_cache[symbol][data_type] = data
    logger.debug(f"Updated cache with {data_type} for {symbol}")


@lru_cache(maxsize=128)
def get_stock_price_from_vnstock(symbol: str) -> Optional[float]:
    """Get stock price using VnStock API.

    Args:
        symbol: Stock symbol.

    Returns:
        Current stock price or None if not found.
    """
    cached_price = get_cached_data("stock_price", symbol)
    if cached_price:
        return cached_price

    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        df = Vnstock().stock(source="TCBS", symbol=symbol).quote.history(
            symbol=symbol, start=start_date, end=end_date, interval="1D"
        )
        logger.debug(f"Found price for {symbol} from TCBS")
        # Multiply by 1000 and convert to int to match original logic
        price = int(float(df.iloc[-1]["close"]) * 1000)
        update_cache("stock_price", symbol, price)
        return price
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return None


@lru_cache(maxsize=128)
def get_company_overview_from_vnstock(symbol: str) -> Optional[str]:
    """Get company overview information using VnStock API.

    Args:
        symbol: Stock symbol.

    Returns:
        Company overview data in markdown format or None if not found.
    """
    cached_overview = get_cached_data("company_overview", symbol)
    if cached_overview:
        return cached_overview

    logger.info(f"Getting company overview for {symbol}")
    try:
        overview = Vnstock().stock(symbol=symbol, source="VCI").company.overview()
        overview_markdown = overview.to_markdown()
        if overview_markdown is None:
            logger.error(f"Could not retrieve overview for symbol {symbol}")
            return None
        update_cache("company_overview", symbol, overview_markdown)
        return overview_markdown
    except Exception as e:
        logger.error(f"Error getting company overview for {symbol}: {e}")
        return None

def finance_client(symbol: str):
    return Vnstock().stock(symbol=symbol, source="VCI")

default_config = {
        "period": "annual",
        "lang": "en",
        "dropna": True
}

def _get_financial_statement_from_vnstock(symbol: str, statement_type: str, vnstock_method: Callable) -> Optional[str]:
    """
    Generic function to get company financial statements (balance sheet, income statement, cash flow)
    using VnStock API and caching.

    Args:
        symbol: Stock symbol.
        statement_type: Type of financial statement (e.g., "financial_statement", "income_statement", "cash_flow_statement") for caching.
        vnstock_method: The specific vnstock.finance method to call (e.g., finance_client(symbol).finance.balance_sheet).

    Returns:
        Company financial statement data in markdown format or None if not found.
    """
    cached_statement = get_cached_data(statement_type, symbol)
    if cached_statement:
        return cached_statement

    try:
        logger.info(f"Getting {statement_type} for {symbol}")
        statement_df = vnstock_method(period=default_config["period"])
        latest_year_data = statement_df.iloc[0] # get the first row (latest year)
        statement = latest_year_data.to_markdown()
        update_cache(statement_type, symbol, statement)
        return statement
    except Exception as e:
        logger.error(f"Error getting {statement_type} for {symbol}: {e}")
        return None


@lru_cache(maxsize=128)
def get_company_financial_statement_from_vnstock(symbol: str) -> Optional[str]:
    """Get company financial statement information using VnStock API.

    Args:
        symbol: Stock symbol.

    Returns:
        Company balance sheet data in markdown format or None if not found.
    """
    return _get_financial_statement_from_vnstock(
        symbol,
        "financial_statement",
        lambda period: finance_client(symbol).finance.balance_sheet(period=period)
    )


@lru_cache(maxsize=128)
def get_company_income_statement_from_vnstock(symbol: str) -> Optional[str]:
    """Get company income statement information using VnStock API.

    Args:
        symbol: Stock symbol.

    Returns:
        Company income statement data in markdown format or None if not found.
    """
    return _get_financial_statement_from_vnstock(
        symbol,
        "income_statement",
        lambda period: finance_client(symbol).finance.income_statement(period=period)
    )


@lru_cache(maxsize=128)
def get_company_cash_flow_statement_from_vnstock(symbol: str) -> Optional[str]:
    """Get company cash flow statement information using VnStock API.

    Args:
        symbol: Stock symbol.

    Returns:
        Company cash flow statement data in markdown format or None if not found.
    """
    return _get_financial_statement_from_vnstock(
        symbol,
        "cash_flow_statement",
        lambda period: finance_client(symbol).finance.cash_flow(period=period)
    )


@tool
def get_current_stock_price(symbol: str) -> float:
    """Get the current stock price of a given symbol.

    This tool retrieves the latest available stock price from the Vietnamese stock market.
    The price is returned in VND (Vietnamese Dong).

    Args:
        symbol: The symbol/ticker of the stock to get the current price for (e.g., "FPT", "VNM").

    Returns:
        The current stock price of the given symbol in VND.

    Raises:
        ValueError: If the stock price cannot be retrieved for the given symbol.
    """
    price = get_stock_price_from_vnstock(symbol)
    logger.info(f"Get stock price for {symbol}: {price}")
    if price is None:
        raise ValueError(f"Could not retrieve stock price for symbol {symbol}")
    return price


@tool
def get_company_financial_statement(symbol: str) -> str:
    """Get the company balance sheet (financial statement) of a given symbol.

    This tool retrieves the balance sheet data which shows the company's assets,
    liabilities, and shareholders' equity at a specific point in time.

    Args:
        symbol: The symbol/ticker of the stock to get the financial statement for (e.g., "FPT", "VNM").

    Returns:
        The company balance sheet in markdown format, showing assets, liabilities, and equity.

    Raises:
        ValueError: If the financial statement cannot be retrieved for the given symbol.
    """
    financial_statement = get_company_financial_statement_from_vnstock(symbol)
    if financial_statement is None:
        raise ValueError(
            f"Could not retrieve financial statement for symbol {symbol}"
        )
    return financial_statement


@tool
def get_company_income_statement(symbol: str) -> str:
    """Get the company income statement of a given symbol.

    This tool retrieves the income statement which shows the company's revenues,
    expenses, and profits over a period of time. It helps assess profitability.

    Args:
        symbol: The symbol/ticker of the stock to get the income statement for (e.g., "FPT", "VNM").

    Returns:
        The company income statement in markdown format, showing revenue, expenses, and profit.

    Raises:
        ValueError: If the income statement cannot be retrieved for the given symbol.
    """
    income_statement = get_company_income_statement_from_vnstock(symbol)
    if income_statement is None:
        raise ValueError(
            f"Could not retrieve income statement for symbol {symbol}"
        )
    return income_statement


@tool
def get_company_overview(symbol: str) -> str:
    """Get the company overview of a given symbol."""
    overview = get_company_overview_from_vnstock(symbol)
    if overview is None:
        raise ValueError(
            f"Could not retrieve company overview for symbol {symbol}"
        )
    return overview


@tool
def get_company_cash_flow_statement(symbol: str) -> str:
    """Get the company cash flow statement of a given symbol.

    This tool retrieves the cash flow statement which shows how changes in balance sheet accounts
    and income affect cash and cash equivalents. It breaks down the analysis into operating,
    investing, and financing activities.

    Args:
        symbol: The symbol/ticker of the stock to get the cash flow statement for (e.g., "FPT", "VNM").

    Returns:
        The company cash flow statement in markdown format, showing operating, investing, and financing cash flows.

    Raises:
        ValueError: If the cash flow statement cannot be retrieved for the given symbol.
    """
    cash_flow_statement = get_company_cash_flow_statement_from_vnstock(symbol)
    if cash_flow_statement is None:
        raise ValueError(
            f"Could not retrieve cash flow statement for symbol {symbol}"
        )
    return cash_flow_statement

def on_exit():
    """Saves the finance data cache on exit."""
    save_finance_data_cache(finance_data_cache)
    logger.info("Finance data cache saved on exit.")

atexit.register(on_exit)


if __name__ == "__main__":
    test_symbols = ["FPT"]

    # logger.info("\nTesting vnstock_price from VnStock API:")
    # for symbol in test_symbols:
    #     try:
    #         price = get_stock_price_from_vnstock(symbol)
    #         financial_statement = get_company_financial_statement(symbol)
    #         logger.info(f"{symbol}: {price}")
    #         logger.info(f"{symbol} financial statement: {financial_statement}")
    #     except Exception as e:
    #         logger.error(f"Error getting current stock price for {symbol}: {e}")
    # get cash flow statement
    # cash_flow_statement = get_company_cash_flow_statement("FPT")
    # # overview = get_company_overview("FPT")
    # fpt_client = finance_client("FPT").finance.cash_flow(period = default_config["period"]) # data frame
    # # get the row 0 of the data frame
    # latest_year = fpt_client.iloc[0]
    # print(latest_year.to_markdown())
    pass