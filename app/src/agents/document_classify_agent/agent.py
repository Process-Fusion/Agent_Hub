from langgraph.types import Command
from src.agents.agent_factory import Agent
from src.agents.document_classify_agent.state import ClassificationAgentState
from src.models.document_human_response_model import DocumentHumanResponseModel
from langgraph.graph import StateGraph
from pathlib import Path
from datetime import date
from src.enums.keyword_type_enum import KeywordTypeEnum
from src.services.postgres_db_service import (
   get_all_classification_keywords,
   get_k_classification_keywords_by_type,
   get_all_classification_types,
   update_hit_count,
   update_miss_count,
   is_type_trusted,
   get_trust_by_classification_type,
   update_classification_keywords_hit,
   update_classification_keywords_miss
)

import base64
from langgraph.types import interrupt
from langchain_openai import ChatOpenAI
from src.agents.document_classify_agent.tool import tool_list, save_extracted_keywords
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import END, START
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.core.env_config import EnvConfig

class DocumentClassifyAgent(Agent):
  def __init__(self):
    self.llm = ChatOpenAI(model="kimi-k2.5", base_url="https://api.moonshot.ai/v1", temperature=0.6, max_tokens=10000, timeout=None, max_retries=3, extra_body={"thinking": {"type": "disabled"}})
    self.graph = self.create_graph()
    self.db_uri = EnvConfig().postgres_connection_string
    self.living_agent = None

  async def _ensure_compiled(self) -> None:
    """`ainvoke` requires AsyncPostgresSaver (`aget_tuple`); compile graph on first async run."""
    if self.living_agent is not None:
      return
    self._async_checkpointer_cm = AsyncPostgresSaver.from_conn_string(conn_string=self.db_uri)
    self.checkpointer = await self._async_checkpointer_cm.__aenter__()
    await self.checkpointer.setup()
    self.living_agent = self.graph.compile(
      checkpointer=self.checkpointer,
    )

  @staticmethod
  def _format_keywords_for_prompt(keywords_by_type: dict) -> str:
    """
    Format keyword models into a readable block for the system prompt.

    Output example:
      Invoice:
        [42] invoice (PRIMARY)
        [43] Bill (SEMANTIC_ALIAS)
        [44] Invoice No. (CONTEXTUAL)
    """
    if not keywords_by_type:
      return ""

    lines = []
    for type_name, keywords in keywords_by_type.items():
      lines.append(f"{type_name}:")
      for kw in keywords:
        # KeywordType may be an int (from DB) or already a string (from model)
        ktype_raw = kw.KeywordType
        if isinstance(ktype_raw, int):
          ktype_label = KeywordTypeEnum(ktype_raw).name
        else:
          ktype_label = str(ktype_raw)
        lines.append(f"  [{kw.KeywordID}] {kw.ClassificationKeyword} ({ktype_label})")
      lines.append("")  # blank line between types

    return "\n".join(lines).rstrip()

  async def build_system_prompt(self) -> str:
    """Build the complete system prompt with all dynamic content."""
    system_prompt_path = Path(__file__).parent / "system_prompt.md"

    # Load template
    template = system_prompt_path.read_text(encoding="utf-8")
    types = await get_all_classification_types()
    # Load and format classification keywords
    keywords_by_type = {}
    for type_name in types:
      keywords_by_type[type_name] = await get_k_classification_keywords_by_type(type_name, k=20)
    if keywords_by_type:
      classification_keywords = self._format_keywords_for_prompt(keywords_by_type)
    else:
      classification_keywords = f"No keywords found. Known types: {', '.join(types)}"

    return template.format(
        classification_keywords=classification_keywords,
        current_date=date.today().isoformat()
    )

  async def arun(self, document_name: str, page_images) -> str:
    """Run the document classification agent."""
    await self._ensure_compiled()
    thread_id = f"{document_name}"
    config = {"configurable": {"thread_id": thread_id}}
    
    content = [{"type": "text", "text": f"Document name: {document_name}"}]
    for img in page_images:
      content.append({
        "type": "image_url",
        "image_url": {"url": f"data:image/png;base64,{img if isinstance(img, str) else base64.b64encode(img).decode()}"}
      })

    result = await self.living_agent.ainvoke(
      {
        "messages": [HumanMessage(content=content)],
        "document_name": document_name
      },
      config=config
    )
    return {
       "classification_type": result["classification_type"],
       "confidence_score": result["confidence_score"],
       "reasoning": result["reasoning"]
    }
  
  async def acomplaint(self, document_name: str, human_response: DocumentHumanResponseModel) -> None:
    """Complaint from human (Human in the loop)
    Main target of complaint is to update the agent knowledge
    """
    await self._ensure_compiled()
    thread_id = f"{document_name}"
    config = {"configurable": {"thread_id": thread_id}}
    # Update Trust System
    await update_miss_count(human_response.agent_classification_type)
    # Update the agent knowledge
    await self.living_agent.ainvoke(
      Command(
        update={
          "human_approved": False,
          "human_correction": human_response.human_correction,
          "classification_type": human_response.agent_classification_type,
        },
        goto="keyword_extraction"
      ),
      config=config
    )

  async def aresume(self, document_name: str, human_response: DocumentHumanResponseModel) -> None:
    """
    Resume from interruption (Human in the loop)
    Main target of resume is to update the agent knowledge
    """
    await self._ensure_compiled()
    thread_id = f"{document_name}"
    config = {"configurable": {"thread_id": thread_id}}
    decision = "approve" if human_response.decision else "correct"
    await self.living_agent.ainvoke(
      Command(resume={
         "decision": decision,
         "document_name": document_name,
         "correct_classification": human_response.final_classification_type
      }),
      config=config
    )

  async def agent(self, state: ClassificationAgentState) -> ClassificationAgentState:
    """AI classification node - classifies document and stores result in state."""
    # Build system prompt fresh each time (to include latest keyword updates)
    main_system_prompt = await self.build_system_prompt()
    llm_with_tools = self.llm.bind_tools(tool_list)
    response = await llm_with_tools.ainvoke(input=[SystemMessage(content=main_system_prompt)] + state.messages)
    
    return {"messages": [response]}

  async def agent_routing(self, state: ClassificationAgentState) -> ClassificationAgentState:
    """Route after agent node based on tool calls or completion."""
    last_message = state.messages[-1] if state.messages else None
    
    if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool"
    
    # Check current skill mode
    next_step = getattr(state, 'next_step', None)
    
    # If in keyword extraction mode, route to extraction handler
    if next_step == "keyword_extraction":
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

  async def human_confirmation(self, state: ClassificationAgentState) -> ClassificationAgentState:
    """Human-in-the-loop node - pause and wait for user confirmation."""
    classification_type = getattr(state, 'classification_type', 'Unknown')
    confidence_score = getattr(state, 'confidence_score', 0.0)
    document_name = getattr(state, 'document_name', 'Unknown')
    
    # Get current trust info
    trust_info = await get_trust_by_classification_type(classification_type)
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
            "is_trusted": await is_type_trusted(classification_type, min_hits=3)
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
            await update_hit_count(classification_type)
            # Human confimed - increment keywords hit count
            await update_classification_keywords_hit(state.keyword_ids)
            return {
                "human_approved": True,
                "human_correction": None,
                "next_step": None
            }
        
        elif decision == "correct":
            # Human rejected - increment miss count and get correction
            await update_miss_count(classification_type)
            # Human rejected - increment keywords miss count
            await update_classification_keywords_miss(state.keyword_ids)
            correct_type = human_response.get("correct_classification", classification_type)
            
            return {
                "human_approved": False,
                "human_correction": correct_type,
                "next_step": "keyword_extraction"  # Switch to keyword extraction mode
            }
    
    # Default: treat as rejection
    await update_miss_count(classification_type)
    await update_classification_keywords_miss(state.keyword_ids)
    return {
        "human_approved": False,
        "human_correction": None,
        "next_step": None
    }

  async def keyword_extraction_agent(self,state: ClassificationAgentState) -> ClassificationAgentState:
    """AI node to extract keywords from document after human correction.
    
    The AI re-analyzes the document with the correct classification type in mind
    and identifies distinguishing keywords/patterns it missed in the first pass.
    """
    human_correction = getattr(state, 'human_correction', None)
    
    if not human_correction:
        # No correction to learn from
        return {"next_step": None}
    
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
        "next_step": None  # Reset to normal mode
    }

  async def check_trust_node(self, state: ClassificationAgentState) -> ClassificationAgentState:
    """Check trust status and update state with routing decision."""
    classification_type = getattr(state, 'classification_type', None)
    confidence_score = getattr(state, 'confidence_score', 0.0)
    
    if not classification_type:
        return {"trust_routing": "classify"}
    
    # Check trust status
    trusted = await is_type_trusted(classification_type, min_hits=3)
    
    if trusted and confidence_score >= 0.85:
        # Auto-classify - no human needed
        await update_hit_count(classification_type)
        await update_classification_keywords_hit(state.keyword_ids)
        return {"trust_routing": "auto_save"}
    else:
        # Not trusted or low confidence - need human confirmation
        return {"trust_routing": "human_confirm"}
  
  async def delete_thread_node(self, state: ClassificationAgentState) -> None:
    await self._ensure_compiled()
    await self.living_agent.checkpointer.adelete_thread(state.document_name)


  def create_graph(self) -> StateGraph:
    # Build the graph
    graph = StateGraph(ClassificationAgentState)

    # Add nodes
    graph.add_node("classify_agent", self.agent)
    graph.add_node("agent_tool_routing", self.agent_tool_routing)
    graph.add_node("check_trust", self.check_trust_node)
    graph.add_node("human_confirmation", self.human_confirmation)
    graph.add_node("keyword_extraction", self.keyword_extraction_agent)
    graph.add_node("delete_thread", self.delete_thread_node)

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
            END: "delete_thread"
        }
    )

    # Tool routing returns to classify_agent (or extraction to result handler)
    graph.add_edge("agent_tool_routing", "classify_agent")

    # Trust check routing
    graph.add_conditional_edges(
        "check_trust",
        lambda state: getattr(state, 'trust_routing', END),
        {
            "auto_save": "delete_thread",
            "human_confirm": "human_confirmation",
            "classify": "classify_agent",
            END: "delete_thread"
        }
    )

    # Human confirmation routes to keyword extraction (if correction) or result handler
    graph.add_conditional_edges(
        "human_confirmation",
        lambda state: getattr(state, 'next_step', END),
        {
            "keyword_extraction": "keyword_extraction",
            END: "delete_thread"
        }
    )

    graph.add_edge("keyword_extraction", "delete_thread")
    graph.add_edge("delete_thread", END)

    return graph
