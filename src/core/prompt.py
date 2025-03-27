"""Prompt templates for the chatbot service."""

from typing import List, Optional

SYSTEM_INSTRUCTION = """You are a helpful financial assistant that can provide information based on financial reports,
    documents, or general knowledge. When answering:

    1. If financial report data is provided, prioritize information from those reports.
    2. If context is provided, use that as secondary information.
    3. If neither financial reports nor context has the answer but you know it, provide a general answer
       based on your financial knowledge.
    4. Be concise and clear in your explanations.
    5. Format financial data in a readable way.
    6. When discussing financial metrics, define them briefly before analyzing them.
    7. If you're unsure, acknowledge the limitations of your knowledge.
    8. If the user asks about a topic that is not related to finance, acknowledge that you are not able to answer that question.
    9. Always answer general financial questions like definitions of P/E ratio, ROI, or other common financial terms.
    10. If analyzing multiple reports, highlight trends and changes over time.
    11. answer questions in the same language as the question.
    12. if the money amount is too big, round it to the nearest million or billion.
    Financial reports, when available, are provided between [FINANCIAL REPORTS] tags.
    Context, when available, is provided between [CONTEXT] tags."""

SYSTEM_INSTRUCTION_FOR_AUTOMATION = """
You are a specialized financial assistant designed to provide accurate, actionable information using external tools, documents, and financial knowledge.

Follow these guidelines when responding:

1.  **Language:** Respond in the same language as the user's query.
2.  **Clarity & Conciseness:** Provide clear, concise explanations focused on the user's specific needs. Prioritize actionable insights over excessive data.
3.  **Data Formatting:** Format financial data in easily readable tables or structured formats when appropriate. Simplify large monetary values (e.g., using millions or billions with appropriate units).
4.  **Metric Definitions:** Briefly define financial metrics before analyzing them (e.g., "P/E ratio - Price-to-Earnings ratio measures...").
5.  **Knowledge Scope:**
    *   Address general financial questions about terms, concepts, and principles using your base knowledge.
    *   Politely redirect non-financial queries, explaining that you specialize in financial information.
6.  **Limitations:** Acknowledge knowledge limitations transparently when you cannot provide reliable information based on available tools, documents, or your internal knowledge.
7.  **Tool Usage:** Utilize the available tool effectively to answer questions requiring specific, up-to-date data.

Available Tool:
- `get_stock_information_by_year(symbol: str, year: Optional[int] = None)`: 
  Retrieves comprehensive financial data for a Vietnamese stock symbol.
  
  Args:
  - symbol: Stock ticker symbol (e.g., "FPT", "VNM", "VIC")
  - year: (Optional) Specific year for historical data. If omitted, returns the latest available data.
  
  Returns:
  - Current stock price
  - Company overview (business description, sector, history)
  - Financial statements (balance sheet, income statement, cash flow)
  - Key financial ratios organized by category (valuation, profitability, liquidity, etc.)
  
  Usage examples:
  - For latest data: get_stock_information_by_year("FPT")
  - For historical data: get_stock_information_by_year("FPT", 2020)
  
  When to use:
  - When asked about a specific Vietnamese company's financial performance
  - When detailed financial analysis is requested
  - When comparing current vs historical financial metrics
  - When asked about financial ratios, company background, or specific financial statements

- `search_information(query: str)`: 
  Searches the web for information relevant to the user's query.
  
  Args:
  - query: The search query
  Returns:
  - str: Organized text content from the top search results, including source URL, title, snippet, and extracted content.

  When to use:
  - For general information, news, or topics not covered by the `get_stock_information_by_year` tool.
  - To find recent news, market trends, or explanations of financial concepts.
  - When the user's query requires up-to-date information from the web that isn't specific company financial data.

"""

def get_system_instruction() -> str:
    """Get the system instruction for the chatbot."""
    return SYSTEM_INSTRUCTION


def build_prompt_with_financial_reports(report_content: str, query: str, conversation_history: List[str] = None, stock_price_info: Optional[str] = None) -> str:
    """Build prompt string with financial report content."""
    financial_reports = f"""[FINANCIAL REPORTS]\n{report_content}\n[/FINANCIAL REPORTS]"""
    prompt_prefix = "Based on the financial reports provided, please answer the following question:"

    if stock_price_info:
        financial_reports += f"\n[STOCK_PRICE]\n{stock_price_info}\n[/STOCK_PRICE]"

    conversation_context = ""
    if conversation_history:
        conversation_context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(conversation_history)}\n[/CONTEXT]\n"""
    
    return f"""{financial_reports}\n\n{conversation_context}{prompt_prefix}\n{query}\n\nIf the financial reports don't contain information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge."""


def build_prompt_with_financial_reports_and_history(statement_content: str, query: str, conversation_history: List[str] = None) -> str:
    """Build prompt string with both financial reports and document context."""
    financial_reports = f"""[FINANCIAL REPORTS]\n{statement_content}\n[/FINANCIAL REPORTS]"""

    prompt_prefix = "Based on the financial reports and additional context provided, please answer the following question:"

    conversation_context = ""
    if conversation_history:
        conversation_context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(conversation_history)}\n[/CONTEXT]\n"""

    return f"""{financial_reports}\n\n{conversation_context}{prompt_prefix}\n{query}\n\nIf neither the financial reports nor the context contains information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge."""


def build_prompt_with_context(document_content: str, query: str, conversation_history: List[str] = None) -> str:
    """Build prompt string with document context."""
    context = f"""[CONTEXT]\n{document_content}\n[/CONTEXT]"""
    prompt_prefix = "Based on the above context, please answer the following question:"
    if conversation_history:
        context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(conversation_history)}\n[/CONTEXT]"""
        prompt_prefix = "Based on the previous conversation, answer the following question:"

    return f"""{context}\n{prompt_prefix}\n{query}\n\nIf neither the context nor the previous conversation contains information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge."""


def build_prompt_without_context(query: str, conversation_history: List[str] = None) -> str:
    """Build prompt string without document context."""
    prompt_prefix = "You are a helpful financial assistant. Please answer the following question to the best of your ability:"
    if conversation_history:
        context = f"""[CONTEXT]\nPrevious conversation:\n{chr(10).join(conversation_history)}\n[/CONTEXT]"""
        prompt_prefix = "Based on the previous conversation, answer the following question:"
    else:
        context = ""

    return f"""{context}\n***{prompt_prefix}***\n{query}"""


def build_prompt_for_missing_financial_report(stock_symbol: str, period: Optional[str], query: str, conversation_history: List[str] = None) -> str:
    """Build prompt string when financial report was requested but not found."""
    period_info = f" for period {period}" if period else ""
    context = f"""[CONTEXT]\nNo financial report was found for {stock_symbol}{period_info}.\n"""

    if conversation_history:
        context += f"Previous conversation:\n{chr(10).join(conversation_history)}\n"

    context += "[/CONTEXT]"

    prompt_prefix = (
        "The user is asking about a financial report that is not available. "
        "Please inform them that the requested financial data is not available "
        "and answer any general financial questions if possible:"
    )

    return f"""{context}\n{prompt_prefix}\n{query}"""


def build_prompt_with_stock_price(stock_symbol: str, period: Optional[str], query: str, stock_price_info: str, conversation_history: List[str] = None) -> str:
    """Build prompt string when only stock price is available."""
    period_info = f" for period {period}" if period else ""
    context = f"""[STOCK_PRICE]\n{stock_price_info}\n"""

    if conversation_history:
        context += f"Previous conversation:\n{chr(10).join(conversation_history)}\n"

    context += "[/STOCK_PRICE]"

    prompt_prefix = (
        "The user is asking about a stock. Please provide information based on the stock price "
        "and answer any general financial questions if possible:"
    )

    return f"""{context}\n{prompt_prefix}\n{query}"""


def build_prompt_for_extract_stock_symbol(query: str) -> str:
    """Build prompt string for extracting stock symbol from query."""
    return f"""[QUERY]\n{query}\n[/QUERY]
    You are a helpful financial assistant that can provide information based on financial reports,
    documents, or general knowledge. When answering:
    - Extract the stock symbol from the query.
    - If the query is not about a stock, return None.
    """
# def build_prompt_with_financial_reports_from_tools(income_statement: str, balance_sheet: str, cash_flow_statement: str, company_overview: str, period: Optional[str] = None) -> str:
#     """Build prompt string with financial report content."""
#     financial_reports = f"""[FINANCIAL REPORTS]\n\
#     Income Statement: {income_statement}\n\
#     Balance Sheet: {balance_sheet}\n\
#     Cash Flow Statement: {cash_flow_statement}\n\
#     Company Overview: {company_overview}\n\
#     [/FINANCIAL REPORTS]"""
#     prompt_prefix = "Based on the financial reports provided, please answer the following question:"
#     return f"""{financial_reports}\n\n{prompt_prefix}\n\nIf the financial reports don't contain information about this question but it's a general financial concept, please provide a helpful answer based on your financial knowledge."""

from typing import List, Optional

def build_prompt_with_tools_for_automation(query: str, conversation_history: Optional[List[str]] = None) -> str:
    """
    Builds the user message prompt for the agent, focusing on the query and conversation history.

    This prompt assumes the agent's core instructions (role, available tools, general behavior)
    are already defined in the system prompt used to initialize the agent. This function
    formats the immediate user request and relevant context (history).

    Args:
        query: The user's current query.
        conversation_history: A list of previous turns in the conversation (optional).
                              Expected format might need adjustment based on how history is stored
                              (e.g., alternating user/assistant messages).

    Returns:
        A formatted string to be used as the content of the user message sent to the agent.
    """
    prompt_parts = []

    # Add a concise instruction guiding the agent for this specific turn.
    prompt_parts.append(
        "Based on the chat history (if provided) and the current query, please provide a helpful response. "
        "Use your available tools if necessary to gather or verify information."
    )

    # Include conversation history if available, clearly demarcated.
    if conversation_history:
        # Join the history turns. Consider adding prefixes like "User:"/"Assistant:"
        # if the history list doesn't already include them and the model benefits from it.
        history_str = "\n".join(conversation_history)
        prompt_parts.append(f"""[CHAT HISTORY]
{history_str}
[/CHAT HISTORY]""")

    # Include the current user query, clearly demarcated.
    prompt_parts.append(f"""[CURRENT QUERY]
{query}
[/CURRENT QUERY]""")

    # Combine the parts into a single string with clear separation.
    return "\n\n".join(prompt_parts)
