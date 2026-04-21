from abc import ABC, abstractmethod
from typing import Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel

class State(BaseModel):
  messages: Annotated[list[BaseMessage], add_messages]

# Product interface 
class Agent(ABC):
  @abstractmethod
  async def arun(self, state: State) -> str:
    pass

  @abstractmethod
  async def agent(self, state: State) -> State:
    pass

  async def agent_tool_routing(self, state: State) -> State:
    pass
  
  @abstractmethod
  def create_graph(self):
    pass

# Factory
class AgentFactory:
  def __init__(self):
    pass

  @abstractmethod
  def create_agent(self, agent_name: str) -> Agent:
    pass
