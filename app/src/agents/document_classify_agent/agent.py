from langgraph.types import Command
from src.agents.agent_factory import Agent
from src.agents.document_classify_agent.state import ClassificationAgentState
from langgraph.graph import StateGraph
from pathlib import Path
from datetime import date
from src.DAL.classification_keywords_DA import get_all_keywords, get_all_types
from src.DAL.classification_trust_system_DA import (
    get_trust_by_type,
    increment_hit_count,
    increment_miss_count,
    is_trusted
)
from langgraph.types import interrupt
from langchain_openai import ChatOpenAI
from src.agents.document_classify_agent.tool import tool_list, save_extracted_keywords
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import END, START
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.infrastructure.postgres_db import get_connection

class DocumentClassifyAgent(Agent):
  def __init__(self):
    self.llm = ChatOpenAI(model="kimi-k2.5", base_url="https://api.moonshot.ai/v1", temperature=0.6, max_tokens=10000, timeout=None, max_retries=3, extra_body={"thinking": {"type": "disabled"}})
    self.graph = self.create_graph()
    self.living_agent = self.graph.compile(checkpointer=AsyncPostgresSaver(conn = get_connection().__enter__()))

  def build_system_prompt(self) -> str:
    """Build the complete system prompt with all dynamic content."""
    system_prompt_path = Path(__file__).parent / "system_prompt.md"

    # Load template
    template = system_prompt_path.read_text(encoding="utf-8")

    # Load classification keywords
    classification_keywords = get_all_keywords()
    classification_types = get_all_types()
    # Format the prompt
    return template.format(
        classification_keywords=classification_keywords if len(classification_keywords.keys()) > 0 else f"No keywords found, here are the types: {classification_types}",
        current_date=date.today().isoformat()
    )

  async def arun(self, thread_id: str, document_name: str, page_images: list[bytes]) -> str:
    """Run the document classification agent."""


  async def agent(self, state: ClassificationAgentState) -> ClassificationAgentState:
    """AI classification node - classifies document and stores result in state."""
    # Build system prompt fresh each time (to include latest skill updates)
    main_system_prompt = self.build_system_prompt()
    llm_with_tools = self.llm.bind_tools(tool_list)
    response = await llm_with_tools.ainvoke(input=[SystemMessage(content=main_system_prompt)] + state.messages)
    
    return {"messages": [response]}

  async def agent_routing(self, state: ClassificationAgentState) -> ClassificationAgentState:
    """Route after agent node based on tool calls or completion."""
    last_message = state.messages[-1] if state.messages else None
    
    if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool"
    
    # Check current skill mode
    active_skill = getattr(state, 'active_skill', None)
    
    # If in keyword extraction mode, route to extraction handler
    if active_skill == "keyword_extraction":
        return "keyword_extraction"
    
    # Check if we have a classification result
    if hasattr(state, 'classification_type') and state.classification_type:
        return "check_trust"
    
    return END

  async def agent_tool_routing(self, state: ClassificationAgentState) -> Command:
    """Handle tool execution and routing."""
    tool_node = ToolNode(tool_list)
    response = await tool_node.ainvoke(state)
    
    if isinstance(response, list) or isinstance(response, Command):
        return response
    return Command(update=response)

  # TODO: Implement human confirmation node
  # Find a way for the agent to communicate with the human (Email?, Team chat?)
  # When waiting for human confirmation, the agent should not continue processing the document
  # Postgres Checkpoint: Insert the conversation history into the database using thread_id and when receive an response from human
  # -> Retrieve the conversation history and continue the graph execution
  async def human_confirmation(self, state: ClassificationAgentState) -> ClassificationAgentState:
    """Human-in-the-loop node - pause and wait for user confirmation."""
    classification_type = getattr(state, 'classification_type', 'Unknown')
    confidence_score = getattr(state, 'confidence_score', 0.0)
    document_name = getattr(state, 'document_name', 'Unknown')
    
    # Get current trust info
    trust_info = get_trust_by_type(classification_type)
    hit_count = trust_info['hitcount'] if trust_info else 0
    miss_count = trust_info['misscount'] if trust_info else 0
    
    # Pause execution and wait for human input
    human_response = interrupt({
        "action": "classification_review",
        "document_name": document_name,
        "proposed_classification": classification_type,
        "confidence_score": confidence_score,
        "trust_info": {
            "hit_count": hit_count,
            "miss_count": miss_count,
            "net_score": hit_count - miss_count,
            "is_trusted": is_trusted(classification_type, min_hits=3)
        },
        "question": f"Approve classification '{classification_type}' with confidence {confidence_score:.2f}?",
        "options": {
            "approve": "Classification is correct - approve and save",
            "correct": "Classification is wrong - provide correct type for AI learning"
        }
    })
    
    # Process human response when resumed
    if isinstance(human_response, dict):
        decision = human_response.get("decision")
        
        if decision == "approve":
            # Human confirmed - increment hit count
            increment_hit_count(classification_type)
            return {
                "human_approved": True,
                "human_correction": None,
                "final_classification": classification_type,
                "active_skill": None
            }
        
        elif decision == "correct":
            # Human rejected - increment miss count and get correction
            increment_miss_count(classification_type)
            correct_type = human_response.get("correct_classification", classification_type)
            
            return {
                "human_approved": False,
                "human_correction": correct_type,
                "final_classification": correct_type,
                "active_skill": "keyword_extraction"  # Switch to keyword extraction mode
            }
    
    # Default: treat as rejection
    increment_miss_count(classification_type)
    return {
        "human_approved": False,
        "human_correction": None,
        "final_classification": classification_type,
        "active_skill": None
    }

  async def keyword_extraction_agent(self,state: ClassificationAgentState) -> ClassificationAgentState:
    """AI node to extract keywords from document after human correction.
    
    The AI re-analyzes the document with the correct classification type in mind
    and identifies distinguishing keywords/patterns it missed in the first pass.
    """
    human_correction = getattr(state, 'human_correction', None)
    
    if not human_correction:
        # No correction to learn from
        return {"active_skill": None}
    
    # Build extraction prompt
    extraction_prompt = f"""You previously classified this document incorrectly. 

    The human has indicated the CORRECT classification is: **{human_correction}**

    Your task is to re-analyze the document and identify specific keywords, patterns, 
    or visual elements that distinguish a "{human_correction}" from other document types.

    Focus on:
    1. Header text or titles
    2. Specific field names or labels
    3. Form structure or layout patterns
    4. Company/vendor names visible
    5. Unique identifiers or numbers (PO #, Invoice #, etc.)
    6. Any other distinguishing text or visual elements

    Extract 3-7 specific keywords or phrases that would help identify this document 
    as a "{human_correction}" in future classifications.

    Use the save_extracted_keywords tool to save your findings.
    """

    # Use tools available for keyword extraction
    llm_with_tools = self.llm.bind_tools([save_extracted_keywords])
    response = await llm_with_tools.ainvoke(
        input=[SystemMessage(content=extraction_prompt)] + state.messages
    )

    return {
        "messages": [response],
        "active_skill": None  # Reset to normal mode
    }

  async def check_trust_node(self, state: ClassificationAgentState) -> ClassificationAgentState:
    """Check trust status and update state with routing decision."""
    classification_type = getattr(state, 'classification_type', None)
    confidence_score = getattr(state, 'confidence_score', 0.0)
    
    if not classification_type:
        return {"trust_routing": "classify"}
    
    # Check trust status
    trusted = is_trusted(classification_type, min_hits=3)
    
    if trusted and confidence_score >= 0.85:
        # Auto-classify - no human needed
        increment_hit_count(classification_type)
        return {"trust_routing": "auto_save"}
    else:
        # Not trusted or low confidence - need human confirmation
        return {"trust_routing": "human_confirm"}

  async def route_from_trust_check(self, state: ClassificationAgentState) -> str:
    """Route based on trust check result from state."""
    trust_routing = getattr(state, 'trust_routing', None)
    if trust_routing:
        return trust_routing
    else:
        return "human_confirm"

  async def handle_result(self, state: ClassificationAgentState) -> ClassificationAgentState:
    """Handle the result after human confirmation, auto-classification, or keyword extraction."""
    human_approved = getattr(state, 'human_approved', False)
    human_correction = getattr(state, 'human_correction', None)
    extracted_keywords = getattr(state, 'extracted_keywords', None)
    
    # If we just finished keyword extraction, we're done
    if extracted_keywords and human_correction:
        return {
            "status": "completed", 
            "approved": False,
            "learned_from_correction": True,
            "correct_type": human_correction,
            "keywords_added": extracted_keywords
        }
    
    # Otherwise, normal completion
    return {
        "status": "completed", 
        "approved": human_approved,
        "classification": getattr(state, 'final_classification', None)
    }

  def create_graph(self):
    # Build the graph
    graph = StateGraph(ClassificationAgentState)

    # Add nodes
    graph.add_node("classify_agent", self.agent)
    graph.add_node("agent_tool_routing", self.agent_tool_routing)
    graph.add_node("check_trust", self.check_trust_node)
    graph.add_node("human_confirmation", self.human_confirmation)
    graph.add_node("keyword_extraction", self.keyword_extraction_agent)
    graph.add_node("keyword_extraction_tool_node", ToolNode([save_extracted_keywords]))
    graph.add_node("handle_result", self.handle_result)

    # Add edges
    graph.add_edge(START, "classify_agent")

    # Conditional routing from classify_agent
    graph.add_conditional_edges(
        "classify_agent",
        self.agent_routing,
        {
            "tool": "agent_tool_routing",
            "check_trust": "check_trust",
            "keyword_extraction": "keyword_extraction",
            END: END
        }
    )

    # Tool routing returns to classify_agent (or extraction to result handler)
    graph.add_edge("agent_tool_routing", "classify_agent")

    # Trust check routing
    graph.add_conditional_edges(
        "check_trust",
        self.route_from_trust_check,
        {
            "auto_save": "handle_result",
            "human_confirm": "human_confirmation",
            "classify": "classify_agent"
        }
    )

    # Human confirmation routes to keyword extraction (if correction) or result handler
    graph.add_conditional_edges(
        "human_confirmation",
        lambda state: "keyword_extraction" if getattr(state, 'human_correction', None) else "handle_result",
        {
            "keyword_extraction": "keyword_extraction",
            "handle_result": "handle_result"
        }
    )

    # Keyword extraction goes to result handler
    graph.add_edge("keyword_extraction", "keyword_extraction_tool_node")
    graph.add_edge("keyword_extraction_tool_node", "handle_result")

    # Result handler ends
    graph.add_edge("handle_result", END)