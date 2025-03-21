from datetime import datetime, timedelta
from typing import Optional, Dict
from functools import lru_cache

from langchain_core.tools import tool
from vnstock import Vnstock
from src.core.config import logger
from vnstock import Listing


@lru_cache(maxsize=128)
def get_stock_price_from_vnstock(symbol: str) -> Optional[float]:
    """
    Get stock price using VnStock API, looping through sources.

    Args:
        symbol (str): Stock symbol

    Returns:
        Optional[float]: Current stock price or None if not found
    """
    sources = ["TCBS", "VCI", "MSN"]
    for source in sources:
        try:
            client = Vnstock()
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            df = client.stock(source=source, symbol=symbol).quote.history(
                symbol=symbol, start=start_date, end=end_date, interval="1D"
            )
            if not df.empty:
                logger.debug(f"Found price for {symbol} from {source}")
                return int(float(df.iloc[-1]["close"]) * 1000)
        except Exception as e:
            logger.error(f"Error getting price for {symbol} from {source}: {e}")
            continue  # Try the next source
    return None


@lru_cache(maxsize=128)
def get_company_overview(symbol: str) -> Optional[Dict]:
    """
    Get company overview information using VnStock API.

    Args:
        symbol (str): Stock symbol

    Returns:
        Optional[Dict]: Company overview data or None if not found.
    """
    try:
        client = Vnstock()
        company = client.stock(symbol=symbol, source="VCI").company
        overview = company.overview()
        return overview
    except Exception as e:
        logger.error(f"Error getting company overview for {symbol}: {e}")
        return None


@lru_cache(maxsize=128)
def get_company_financial_statement_from_vnstock(symbol: str) -> Optional[str]:
    """
    Get company financial statement information using VnStock API.

    Args:
        symbol (str): Stock symbol

    Returns:
        Optional[str]: Company balance sheet data in markdown format or None if not found
    """
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        financial_statement = stock.finance.balance_sheet(period='annual', lang='en',dropna = True)
        return financial_statement.to_markdown()
    except Exception as e:
        logger.error(f"Error getting financial statement for {symbol}: {e}")
        return None


@lru_cache(maxsize=128)
def get_company_income_statement_from_vnstock(symbol: str) -> Optional[str]:
    """
    Get company income statement information using VnStock API.

    Args:
        symbol (str): Stock symbol

    Returns:
        Optional[str]: Company income statement data in markdown format or None if not found
    """
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        income_statement = stock.finance.income_statement(period='annual', lang='en',dropna = True)
        return income_statement.to_markdown()
    except Exception as e:
        logger.error(f"Error getting income statement for {symbol}: {e}")
        return None


@lru_cache(maxsize=128)
def get_company_cash_flow_statement_from_vnstock(symbol: str) -> Optional[str]:
    """
    Get company cash flow statement information using VnStock API.

    Args:
        symbol (str): Stock symbol

    Returns:
        Optional[str]: Company cash flow statement data in markdown format or None if not found
    """
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        cash_flow_statement = stock.finance.cash_flow(period='annual', lang='en',dropna = True)
        return cash_flow_statement.to_markdown()
    except Exception as e:
        logger.error(f"Error getting cash flow statement for {symbol}: {e}")
        return None

@lru_cache(maxsize=128)
def get_company_overview_from_vnstock(symbol: str) -> str:
    """
    Get company overview information using VnStock API.

    Args:
        symbol (str): Stock symbol

    Returns:
        Optional[str]: Company overview data in markdown format or None if not found.
    """
    company = Vnstock().stock(symbol=symbol, source='VCI').company
    overview = company.overview()
    overview_markdown = overview.to_markdown()
    if overview_markdown is None:
        logger.error(f"Could not retrieve overview for symbol {symbol}")
        return None
    return overview_markdown

@tool
def get_current_stock_price(symbol: str) -> float:
    """
    Get the current stock price of a given symbol.
    
    This tool retrieves the latest available stock price from the Vietnamese stock market.
    The price is returned in VND (Vietnamese Dong).

    Args:
        symbol (str): The symbol/ticker of the stock to get the current price for (e.g., "FPT", "VNM")

    Returns:
        float: The current stock price of the given symbol in VND

    Raises:
        ValueError: If the stock price cannot be retrieved for the given symbol
    """
    price = get_stock_price_from_vnstock(symbol)
    if price is None:
        raise ValueError(f"Could not retrieve stock price for symbol {symbol}")
    return price

@tool
def get_company_financial_statement(symbol: str) -> str:
    """
    Get the company balance sheet (financial statement) of a given symbol.
    
    This tool retrieves the balance sheet data which shows the company's assets, 
    liabilities, and shareholders' equity at a specific point in time.

    Args:
        symbol (str): The symbol/ticker of the stock to get the financial statement for (e.g., "FPT", "VNM")

    Returns:
        str: The company balance sheet in markdown format, showing assets, liabilities, and equity

    Raises:
        ValueError: If the financial statement cannot be retrieved for the given symbol
    """
    financial_statement = get_company_financial_statement_from_vnstock(symbol)
    if financial_statement is None:
        raise ValueError(f"Could not retrieve financial statement for symbol {symbol}")
    return financial_statement


@tool
def get_company_income_statement(symbol: str) -> str:
    """
    Get the company income statement of a given symbol.
    
    This tool retrieves the income statement which shows the company's revenues, 
    expenses, and profits over a period of time. It helps assess profitability.

    Args:
        symbol (str): The symbol/ticker of the stock to get the income statement for (e.g., "FPT", "VNM")

    Returns:
        str: The company income statement in markdown format, showing revenue, expenses, and profit

    Raises:
        ValueError: If the income statement cannot be retrieved for the given symbol
    """
    income_statement = get_company_income_statement_from_vnstock(symbol)
    if income_statement is None:
        raise ValueError(f"Could not retrieve income statement for symbol {symbol}")
    return income_statement
@tool
def get_company_overview(symbol: str) -> str:
    """
    Get the company overview of a given symbol.
    """
    overview = get_company_overview_from_vnstock(symbol)
    return overview

@tool
def get_company_cash_flow_statement(symbol: str) -> str:
    """
    Get the company cash flow statement of a given symbol.
    
    This tool retrieves the cash flow statement which shows how changes in balance sheet accounts
    and income affect cash and cash equivalents. It breaks down the analysis into operating,
    investing, and financing activities.

    Args:
        symbol (str): The symbol/ticker of the stock to get the cash flow statement for (e.g., "FPT", "VNM")

    Returns:
        str: The company cash flow statement in markdown format, showing operating, investing, and financing cash flows

    Raises:
        ValueError: If the cash flow statement cannot be retrieved for the given symbol
    """
    cash_flow_statement = get_company_cash_flow_statement_from_vnstock(symbol)
    if cash_flow_statement is None:
        raise ValueError(f"Could not retrieve cash flow statement for symbol {symbol}")
    return cash_flow_statement

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
    
    # financial_statement = get_company_financial_statement("FPT")
    overview = get_company_overview("FPT")
    print(overview)