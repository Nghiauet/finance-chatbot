# src/core/agent_manager.py
from src.services.agent import QueryAgent
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
agent = QueryAgent(memory=memory)