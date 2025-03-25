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