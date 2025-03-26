from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from typing import AsyncGenerator

from src.core.config import llm_config
from src.services.tools.toolbox import (
    get_current_stock_price,
    get_company_balance_sheet,
    get_company_income_statement,
    get_company_cash_flow_statement,
    get_company_overview,
    get_company_ratio,
)
from loguru import logger
from src.core.config import llm_config
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
            model=llm_config.default_model,  # or llm_config.default_model
            streaming=True,
        )
        self.memory = memory
        self.tools = [
            get_current_stock_price,
            get_company_balance_sheet,
            get_company_income_statement,
            get_company_cash_flow_statement,
            get_company_overview,
        ]

        instruction = """
You are a financial advisor specializing in the Vietnamese stock market. Provide detailed, data-driven analysis to help users make informed investment decisions.

- Base all conclusions on data from the tools.
- Respond in the user's language.
- When an investment philosophy is mentioned (e.g., value investing), tailor your analysis accordingly and explain your methodology.
- available tools:
    - get_current_stock_price
    - get_company_balance_sheet
    - get_company_income_statement
    - get_company_cash_flow_statement
    - get_company_overview
"""

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

    # async def async_stream_answer(self, question: str, session_id: str) -> AsyncGenerator[str, None]:
    #     """
    #     Streams the agent's response in chunks.
    #     """
    #     config = {"configurable": {"thread_id": session_id}}
    #     async for step in self.graph.astream(
    #         {"messages": [HumanMessage(content=question)]}, config, stream_mode="values"
    #     ):
    #         if "messages" in step and step["messages"]:
    #             if step["messages"][-1].pretty_print():
    #                 yield step["messages"][-1].pretty_print()


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
