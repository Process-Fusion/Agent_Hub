import os
import asyncio
import base64
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT")
os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
os.environ["LANGSMITH_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT")

from agent.agent import graph
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, Interrupt

# Try to import pdf2image, fall back to alternative methods
try:
    from pdf2image import convert_from_path
    PDF_CONVERTER = "pdf2image"
except ImportError:
    try:
        import fitz  # PyMuPDF
        PDF_CONVERTER = "pymupdf"
    except ImportError:
        PDF_CONVERTER = None
        print("Warning: No PDF converter available. Install pdf2image or PyMuPDF.")


def encode_image_to_base64(image_data: bytes, ext: str = "png") -> str:
    """Encode image bytes as a base64 data URL."""
    return f"data:image/{ext};base64,{base64.b64encode(image_data).decode('utf-8')}"


def convert_pdf_page_to_image_pymupdf(pdf_path: str, page_num: int = 0) -> bytes:
    """Convert a PDF page to image using PyMuPDF (fitz)."""
    import fitz
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    # Render page at 150 DPI for good quality
    mat = fitz.Matrix(150 / 72, 150 / 72)
    pix = page.get_pixmap(matrix=mat)
    image_bytes = pix.tobytes("png")
    doc.close()
    return image_bytes


def convert_pdf_page_to_image(pdf_path: str, page_num: int = 0) -> bytes:
    """Convert a PDF page to image bytes.

    Always tries PyMuPDF first (no poppler required).
    Falls back to pdf2image only if PyMuPDF is not available.
    """
    # Try PyMuPDF first (no external dependencies)
    try:
        import fitz
        return convert_pdf_page_to_image_pymupdf(pdf_path, page_num)
    except ImportError:
        pass


def convert_all_pdf_pages_to_images(pdf_path: str, max_pages: int = 10) -> list[bytes]:
    """Convert all pages of a PDF to images.

    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to convert (default 10 for performance)

    Returns:
        List of image bytes, one per page
    """
    page_count = get_pdf_page_count(pdf_path)
    pages_to_convert = min(page_count, max_pages)

    print(f"  Converting {pages_to_convert} of {page_count} page(s)...")

    images = []
    for page_num in range(pages_to_convert):
        try:
            image_bytes = convert_pdf_page_to_image(pdf_path, page_num)
            images.append(image_bytes)
        except Exception as e:
            print(f"  Warning: Failed to convert page {page_num + 1}: {e}")

    return images


def get_pdf_page_count(pdf_path: str) -> int:
    """Get the number of pages in a PDF.

    Always uses PyMuPDF if available (no external dependencies like poppler).
    Falls back to pdf2image only if PyMuPDF is not installed.
    """
    # Try PyMuPDF first (no poppler required)
    try:
        import fitz
        doc = fitz.open(pdf_path)
        count = doc.page_count
        doc.close()
        return count
    except ImportError:
        pass


def display_images_for_review(page_images: list[bytes], doc_name: str):
    """
    Save and display document images for human review.
    Opens images in the default system image viewer.
    
    Args:
        page_images: List of image bytes for each page
        doc_name: Name of the document being reviewed
    """
    import tempfile
    import platform
    import subprocess
    from pathlib import Path
    
    if not page_images:
        print("  [No images to display]")
        return
    
    print(f"\n  Opening {len(page_images)} page(s) for review...")
    
    # Create temp directory for this review session
    temp_dir = tempfile.mkdtemp(prefix="doc_review_")
    
    image_paths = []
    for idx, image_bytes in enumerate(page_images):
        # Save each page as a temp file
        page_filename = f"page_{idx + 1}_of_{len(page_images)}.png"
        image_path = Path(temp_dir) / page_filename
        
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        
        image_paths.append(str(image_path))
        print(f"    Page {idx + 1}: {image_path}")
    
    # Try to open images with default viewer
    system = platform.system()
    try:
        for img_path in image_paths:
            if system == "Windows":
                subprocess.Popen(["start", img_path], shell=True)
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", img_path])
            else:  # Linux
                subprocess.Popen(["xdg-open", img_path])
        print(f"\n  Images opened in default viewer from: {temp_dir}")
        print(f"  (Temp folder will be cleaned up on system restart)")
    except Exception as e:
        print(f"  Could not auto-open images: {e}")
        print(f"  Images saved at: {temp_dir}")
        print(f"  Please open them manually to review.")
    
    print()


def get_user_input(interrupt_info: dict, page_images: list[bytes] = None) -> dict:
    """
    Get user input for classification confirmation.
    Simplified interface - user only approves or provides correction, AI handles keyword extraction.
    
    Args:
        interrupt_info: The interrupt payload from the graph
        page_images: Optional list of image bytes to display for review
    
    Returns:
        User response dict with decision and correction
    """
    print("\n" + "="*60)
    print("HUMAN REVIEW REQUIRED")
    print("="*60)
    print(f"Document: {interrupt_info.get('document_name', 'Unknown')}")
    print(f"Proposed Classification: {interrupt_info.get('proposed_classification', 'Unknown')}")
    print(f"Confidence Score: {interrupt_info.get('confidence_score', 0):.2f}")
    
    trust_info = interrupt_info.get('trust_info', {})
    print(f"Trust Status: Hits={trust_info.get('hit_count', 0)}, " +
          f"Misses={trust_info.get('miss_count', 0)}, " +
          f"Net={trust_info.get('net_score', 0)}")
    print(f"Is Trusted: {trust_info.get('is_trusted', False)}")
    print("-"*60)
    print(interrupt_info.get('question', 'Approve this classification?'))
    print("-"*60)
    
    # Display images if provided
    if page_images:
        display_images_for_review(page_images, interrupt_info.get('document_name', 'Unknown'))
    
    while True:
        choice = input("\n[A]pprove or [C]orrect? ").strip().upper()
        
        if choice in ["A", "APPROVE"]:
            return {
                "decision": "approve"
            }
        
        elif choice in ["C", "CORRECT"]:
            correct_type = input("What is the correct classification type? ").strip()
            if correct_type:
                print(f"AI will now analyze the document to extract distinguishing keywords for '{correct_type}'...")
                return {
                    "decision": "correct",
                    "correct_classification": correct_type
                }
            else:
                print("Please provide a valid classification type.")
        
        else:
            print("Invalid choice. Please enter A (Approve) or C (Correct).")


async def process_document_with_hitl(pdf_path: str, thread_id: str):
    """
    Process a PDF document with human-in-the-loop support.
    Streams responses and handles interrupts for human confirmation.
    """
    # Compile graph with checkpointer (REQUIRED for interrupts)
    checkpointer = MemorySaver()
    compiled_graph = graph.compile(checkpointer=checkpointer)
    
    print(f"\nProcessing: {pdf_path}")
    
    # Convert PDF to images
    page_images = convert_all_pdf_pages_to_images(pdf_path)
    if not page_images:
        raise ValueError("No pages could be converted from PDF")
    
    doc_name = Path(pdf_path).name
    
    # Build message content with all pages
    message_content = [
        {"type": "text", "text": f"Classify the document: {doc_name}\n\nThis document has {len(page_images)} page(s). Review all pages and provide ONE classification for the entire document."}
    ]
    
    for page_idx, image_bytes in enumerate(page_images):
        image_url = encode_image_to_base64(image_bytes, "png")
        message_content.append({
            "type": "text",
            "text": f"\n--- Page {page_idx + 1} ---"
        })
        message_content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
    
    message = HumanMessage(content=message_content)
    
    # Initial input
    initial_input = {
        "messages": [message],
        "active_skill": "main_agent",
        "document_name": doc_name
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Stream with interrupt handling
    current_input = initial_input
    loop_count = 0
    max_loops = 10  # Safety limit
    
    while loop_count < max_loops:
        loop_count += 1
        print(f"\n[Loop {loop_count}] Running graph...")
        
        # Track state during streaming
        interrupt_detected = False
        interrupt_info = None
        final_update = None
        
        # Stream the graph execution - collect all chunks to avoid GeneratorExit from break
        stream_chunks = []
        async for chunk in compiled_graph.astream(
            current_input,
            config=config,
            stream_mode=["messages", "updates"],
            version="v2"
        ):
            stream_chunks.append(chunk)
            
            # Handle different chunk types immediately
            if chunk.get("type") == "messages":
                # Stream AI response tokens
                msg_chunk = chunk.get("data", {})
                if hasattr(msg_chunk, 'content'):
                    print(msg_chunk.content, end="", flush=True)
            
            elif chunk.get("type") == "updates":
                update_data = chunk.get("data", {})
                
                # Check for interrupt
                if "__interrupt__" in update_data:
                    interrupt_info = update_data["__interrupt__"][0].value
                    print("\n\n[INTERRUPT - Waiting for human input]\n")
                    interrupt_detected = True
                    # Note: Don't break - let the stream complete naturally
                    continue
                
                # Check for keyword extraction feedback
                if "extracted_keywords" in update_data:
                    keywords = update_data["extracted_keywords"]
                    print(f"\n✓ AI extracted keywords: {', '.join(keywords)}")
                    print(f"✓ Keywords saved to database for type '{update_data.get('human_correction', 'Unknown')}'")
                
                # Check if completed
                if update_data.get("status") == "completed":
                    final_update = update_data
        
        # Handle results after stream completes
        if interrupt_detected and interrupt_info:
            # Get user input (approve or correct) - pass images for display
            user_response = get_user_input(interrupt_info, page_images)
            
            # Prepare to resume with user response
            current_input = Command(resume=user_response)
            continue  # Go to next loop iteration to resume
        
        if final_update:
            print("\n[CLASSIFICATION COMPLETED]")
            return final_update
        
        # No interrupt, check if we're done
        print("\n[Processing complete]")
        return stream_chunks[-1] if stream_chunks else None
    
    print(f"\n[Reached max loops ({max_loops})]")
    return None


async def main():
    """Main entry point for document classification with HITL."""
    docs_dir = Path("documents_need_classify")
    
    if not docs_dir.exists():
        print(f"Directory not found: {docs_dir}")
        return
    
    # Find all PDF files
    pdf_files = list(docs_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {docs_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF(s) to process")
    print("Human-in-the-Loop mode enabled")
    print("Workflow:")
    print("  1. AI classifies document")
    print("  2. If not trusted/confident, human reviews")
    print("  3. If human corrects, AI extracts new keywords automatically")
    print("-" * 60)
    
    # Process each PDF
    for idx, pdf_path in enumerate(pdf_files, 1):
        try:
            result = await process_document_with_hitl(
                str(pdf_path),
                thread_id=f"doc-classification-{idx}"
            )
            print(f"\n✓ Completed: {pdf_path.name}")
            
            if result:
                status = result.get('status', 'unknown')
                approved = result.get('approved', False)
                if result.get('learned_from_correction'):
                    print(f"  Learned from correction: {result.get('correct_type')}")
                    print(f"  Keywords added: {len(result.get('keywords_added', []))}")
                print(f"  Status: {status}, Approved: {approved}")
        
        except KeyboardInterrupt:
            print(f"\n\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"\n✗ Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("All documents processed!")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExited by user.")
