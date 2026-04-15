import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT")
os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
os.environ["LANGSMITH_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT")

from agent.learning_agent import graph as learning_graph
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver


async def start_learning():
    """Start the learning process by invoking the learning agent."""
    print("=" * 60)
    print("Starting Learning Process")
    print("=" * 60)

    # Set up checkpointer for state management
    checkpointer = MemorySaver()
    compiled_graph = learning_graph.compile(checkpointer=checkpointer)

    # Initial message to trigger the learning agent
    # The agent will load agent reasoning, human reasoning, and cognitive automatically
    initial_message = HumanMessage(content="""
Start the learning process.

Please:
1. Load all agent reasoning files from agent_classification_reasoning/
2. Load all human reasoning files from human_reasoning/
3. Load current classification cognitive rules
4. Compare agent vs human reasoning
5. Identify gaps and update cognitive rules using update_my_cognitive tool if needed

Provide a summary of what you learned and what was updated.
""")

    try:
        result = await compiled_graph.ainvoke(
            {"messages": [initial_message]},
            config={"configurable": {"thread_id": "learning-session-1"}}
        )

        print("\n" + "=" * 60)
        print("Learning Process Completed")
        print("=" * 60)

        # Print the final response
        if result.get("messages"):
            final_message = result["messages"][-1]
            if hasattr(final_message, "content"):
                print(f"\nLearning Summary:\n{final_message.content}")

        return result

    except Exception as e:
        print(f"\n✗ Error during learning process: {e}")
        raise


async def main():
    """Main entry point for the learning script."""
    # Check if reasoning files exist
    agent_dir = Path("agent/agent_classification_reasoning")
    human_dir = Path("agent/human_reasoning")

    print("Checking for reasoning files...")

    if not agent_dir.exists() or not any(agent_dir.glob("*.md")):
        print(f"⚠ No agent reasoning files found in {agent_dir}")
        print("Please run the classification agent first.")
        return

    if not human_dir.exists() or not any(human_dir.glob("*.md")):
        print(f"⚠ No human reasoning files found in {human_dir}")
        print("Please add human reasoning files before starting learning.")
        return

    agent_count = len(list(agent_dir.glob("*.md")))
    human_count = len(list(human_dir.glob("*.md")))

    print(f"✓ Found {agent_count} agent reasoning file(s)")
    print(f"✓ Found {human_count} human reasoning file(s)")
    print()

    # Start the learning process
    await start_learning()

    print("\nLearning session complete!")


if __name__ == "__main__":
    asyncio.run(main())
