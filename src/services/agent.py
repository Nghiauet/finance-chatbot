from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from typing import AsyncGenerator

from src.core.config import llm_config
from src.services.tools.toolbox import (
    get_current_stock_price,
    get_company_financial_statement,
    get_company_income_statement,
    get_company_cash_flow_statement,
    get_company_overview,
)
from loguru import logger

# Load environment variables
load_dotenv(override=True)


class QueryAgent:
    """
    A financial analysis agent specializing in the Vietnamese stock market.
    """

    def __init__(self, memory: MemorySaver):
        """
        Initializes the QueryAgent with an LLM, memory, and tools.
        """
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",  # or llm_config.default_model
            streaming=True,
        )
        self.memory = memory
        self.tools = [
            get_current_stock_price,
            get_company_financial_statement,
            get_company_income_statement,
            get_company_cash_flow_statement,
            get_company_overview,
        ]

        instruction = """You are a sophisticated financial analysis assistant specializing in the Vietnamese stock market. 
        You have access to real-time financial data through the following tools:
        - If need more information, you can use the following tools
        - Just use the tools if you need to, don't need to ask user for confirmation.
        AVAILABLE TOOLS:
        1. get_current_stock_price - Retrieves real-time stock prices in VND
        2. get_company_financial_statement - Obtains balance sheet data showing assets, liabilities, and equity
        3. get_company_income_statement - Obtains revenue, expenses, and profit information
        4. get_company_cash_flow_statement - Obtains data on operating, investing, and financing cash flows
        5. get_company_overview - Obtains general company information and key metrics

        ANALYSIS FRAMEWORK:
        - For comprehensive company analysis, gather all three financial statements
        - For profitability assessment: Focus on income statements, margins, and ROE/ROA
        - For financial stability: Examine balance sheets, debt ratios, and asset quality
        - For operational efficiency: Analyze cash flow statements and working capital
        - For valuation: Consider P/E ratio, P/B ratio, and dividend yields with current price

        RESPONSE QUALITY:
        - Provide data-driven insights rather than general observations
        - Compare key metrics to industry benchmarks when possible
        - Identify specific strengths, weaknesses, opportunities, and threats
        - Consider macroeconomic factors affecting the Vietnamese market
        - Explain financial implications in accessible language
        
        Always respond in the same language as the user's query. If analyzing in a specific investment style (value investing, growth investing, etc.), adjust your focus accordingly and explain your methodology."""

        self.graph = create_react_agent(
            model=self.llm,
            tools=self.tools,
            checkpointer=self.memory,
            prompt=instruction,
        )

    def _get_answer(self, question: str, session_id: str) -> str:
        """
        Retrieves an answer from the agent for a given question and session ID.
        """
        config = {"configurable": {"thread_id": session_id}}
        inputs = {"messages": [HumanMessage(content=question)]}
        response = self.graph.invoke(inputs, config)
        return response["messages"][-1].content

    async def async_stream_answer(self, question: str, session_id: str) -> AsyncGenerator[str, None]:
        """
        Streams the agent's response in chunks.
        """
        config = {"configurable": {"thread_id": session_id}}
        async for step in self.graph.astream(
            {"messages": [HumanMessage(content=question)]}, config, stream_mode="values"
        ):
            if "messages" in step and step["messages"]:
                yield step["messages"][-1].pretty_print()


async def main():
    """
    Example usage of the QueryAgent.
    """
    memory = MemorySaver()
    agent = QueryAgent(memory=memory)
    response = agent.async_stream_answer("Giá cổ phiếu FPT?", "123")
    async for r in response:
        print(r)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
