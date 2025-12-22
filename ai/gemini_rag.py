"""
Gemini File Search RAG Integration
===================================

Uses Gemini File Search API for RAG-powered visa knowledge retrieval.
This replaces complex DIY RAG setups with a managed solution.

Benefits:
- Automatic chunking and embeddings
- Managed vector storage (no external DB needed)
- Built-in semantic search
- Automatic citations in responses
- Cost effective: Free storage, $0.15/1M tokens for indexing

Setup:
1. pip install google-genai
2. Get API key from https://aistudio.google.com/apikey
3. Set GOOGLE_API_KEY environment variable
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for google-genai
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-genai not installed. Install with: pip install google-genai")


class GeminiRAG:
    """
    RAG system using Gemini File Search API.

    This provides a managed RAG solution that:
    - Automatically chunks and embeds documents
    - Stores embeddings in managed vector storage
    - Provides semantic search with citations
    """

    STORE_NAME = "visa_exhibit_knowledge"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini RAG client.

        Args:
            api_key: Google API key (or use GOOGLE_API_KEY env var)
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("google-genai not installed. Run: pip install google-genai")

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set. Get one at https://aistudio.google.com/apikey")

        self.client = genai.Client(api_key=self.api_key)
        self.store = None
        self._init_store()

    def _init_store(self):
        """Initialize or get existing knowledge store."""
        try:
            # Try to find existing store
            stores = list(self.client.file_search_stores.list())
            for store in stores:
                if store.display_name == self.STORE_NAME:
                    self.store = store
                    logger.info(f"Using existing store: {store.name}")
                    return

            # Create new store
            self.store = self.client.file_search_stores.create(
                config={"display_name": self.STORE_NAME}
            )
            logger.info(f"Created new store: {self.store.name}")

        except Exception as e:
            logger.error(f"Failed to initialize store: {e}")
            self.store = None

    def index_document(
        self,
        file_path: str,
        display_name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Index a document into the knowledge store.

        Args:
            file_path: Path to document (PDF, DOCX, TXT, MD, etc.)
            display_name: Optional display name for the document
            metadata: Optional metadata for filtering

        Returns:
            Dict with indexing result
        """
        if not self.store:
            return {"success": False, "error": "Store not initialized"}

        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            config = {
                "display_name": display_name or Path(file_path).name
            }
            if metadata:
                config["custom_metadata"] = metadata

            document = self.client.file_search_stores.upload_document(
                file_search_store=self.store.name,
                file_path=file_path,
                config=config
            )

            logger.info(f"Indexed document: {document.name}")
            return {
                "success": True,
                "document_name": document.name,
                "display_name": config["display_name"]
            }

        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return {"success": False, "error": str(e)}

    def index_text(
        self,
        text: str,
        name: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Index text content into the knowledge store.

        Args:
            text: Text content to index
            name: Name for the content
            metadata: Optional metadata for filtering

        Returns:
            Dict with indexing result
        """
        import tempfile

        # Save text to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text)
            temp_path = f.name

        try:
            result = self.index_document(temp_path, name, metadata)
            return result
        finally:
            os.unlink(temp_path)

    def query(
        self,
        question: str,
        model: str = "gemini-2.5-flash",
        metadata_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query the knowledge store with RAG.

        Args:
            question: The question to ask
            model: Gemini model to use (gemini-2.5-flash or gemini-2.5-pro)
            metadata_filter: Optional metadata filter string

        Returns:
            Dict with answer and sources
        """
        if not self.store:
            return {"success": False, "error": "Store not initialized"}

        try:
            # Build tool config
            file_search_config = {
                "file_search_store_names": [self.store.name]
            }
            if metadata_filter:
                file_search_config["metadata_filter"] = metadata_filter

            response = self.client.models.generate_content(
                model=model,
                contents=question,
                config={
                    "tools": [{
                        "file_search": file_search_config
                    }]
                }
            )

            # Extract answer and sources
            answer = response.text if hasattr(response, 'text') else str(response)

            sources = []
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    for chunk in candidate.grounding_metadata.grounding_chunks:
                        if hasattr(chunk, 'retrieved_context'):
                            sources.append({
                                "uri": chunk.retrieved_context.uri,
                                "title": getattr(chunk.retrieved_context, 'title', '')
                            })

            return {
                "success": True,
                "answer": answer,
                "sources": sources,
                "model": model
            }

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {"success": False, "error": str(e)}

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the knowledge store."""
        if not self.store:
            return []

        try:
            docs = list(self.client.file_search_stores.list_documents(
                file_search_store=self.store.name
            ))
            return [
                {
                    "name": doc.name,
                    "display_name": doc.display_name,
                    "state": doc.state
                }
                for doc in docs
            ]
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []

    def delete_document(self, document_name: str) -> bool:
        """Delete a document from the store."""
        try:
            self.client.file_search_stores.delete_document(name=document_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False


# Convenience functions for visa-specific RAG

def create_visa_knowledge_store(
    api_key: Optional[str] = None,
    knowledge_base_path: Optional[str] = None
) -> Optional[GeminiRAG]:
    """
    Create and populate a visa knowledge store.

    Args:
        api_key: Google API key
        knowledge_base_path: Path to knowledge base files

    Returns:
        Initialized GeminiRAG instance or None
    """
    try:
        rag = GeminiRAG(api_key)

        # Index knowledge base files if provided
        if knowledge_base_path and os.path.exists(knowledge_base_path):
            if os.path.isdir(knowledge_base_path):
                # Index all files in directory
                for file_path in Path(knowledge_base_path).glob("*"):
                    if file_path.suffix.lower() in ['.md', '.txt', '.pdf', '.docx']:
                        rag.index_document(str(file_path))
            else:
                # Single file
                rag.index_document(knowledge_base_path)

        return rag

    except Exception as e:
        logger.error(f"Failed to create knowledge store: {e}")
        return None


def query_visa_knowledge(
    question: str,
    visa_type: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query visa knowledge with context.

    Args:
        question: The question to ask
        visa_type: Optional visa type for context (O-1A, P-1A, etc.)
        api_key: Google API key

    Returns:
        Dict with answer and sources
    """
    try:
        rag = GeminiRAG(api_key)

        # Add visa type context if provided
        if visa_type:
            question = f"For a {visa_type} visa petition: {question}"

        return rag.query(question)

    except Exception as e:
        logger.error(f"Query failed: {e}")
        return {"success": False, "error": str(e)}


# Visa-specific knowledge extraction functions

def get_criterion_requirements(
    visa_type: str,
    criterion: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get regulatory requirements for a specific criterion.

    Args:
        visa_type: Visa type (O-1A, O-1B, P-1A, EB-1A, etc.)
        criterion: Criterion letter or name (A, B, C, etc.)
        api_key: Google API key

    Returns:
        Dict with regulatory text and citation
    """
    question = f"""
    What are the specific regulatory requirements for Criterion {criterion}
    under {visa_type} visa classification?

    Include:
    1. The exact regulatory text from 8 CFR
    2. The CFR citation
    3. What evidence satisfies this criterion
    4. AAO decisions that interpret this criterion
    """

    return query_visa_knowledge(question, visa_type, api_key)


def get_exhibit_order_recommendation(
    visa_type: str,
    exhibit_categories: List[str],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get recommended exhibit ordering based on visa type.

    Args:
        visa_type: Visa type
        exhibit_categories: List of exhibit categories
        api_key: Google API key

    Returns:
        Dict with recommended order
    """
    categories_str = ", ".join(exhibit_categories)
    question = f"""
    For a {visa_type} visa petition, what is the recommended order for
    exhibits in these categories: {categories_str}?

    Provide:
    1. Recommended order (most important first)
    2. Reasoning for the order
    3. Which criteria each category addresses
    """

    return query_visa_knowledge(question, visa_type, api_key)


def get_comparable_evidence_guidance(
    visa_type: str,
    criterion: str,
    field: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get guidance on comparable evidence for a criterion.

    Args:
        visa_type: Visa type
        criterion: Criterion that doesn't readily apply
        field: Beneficiary's field
        api_key: Google API key

    Returns:
        Dict with comparable evidence guidance
    """
    # P-1A has NO comparable evidence provision
    if visa_type == "P-1A":
        return {
            "success": True,
            "answer": "P-1A visa classification does not have a comparable evidence provision. "
                     "All evidence must directly satisfy one of the standard criteria.",
            "comparable_allowed": False
        }

    question = f"""
    For a {visa_type} visa petition in the field of {field}, provide guidance
    on using comparable evidence for Criterion {criterion}.

    Include:
    1. The comparable evidence regulation citation
    2. Why the standard criterion might not apply to this field
    3. What types of evidence would be comparable
    4. How to structure the comparable evidence explanation letter
    5. Example cases where comparable evidence was accepted
    """

    result = query_visa_knowledge(question, visa_type, api_key)
    result["comparable_allowed"] = True
    return result


# Index the project's knowledge base on import
def _auto_index_knowledge_base():
    """Auto-index project knowledge base if Gemini is available."""
    if not GEMINI_AVAILABLE:
        return

    # Check for API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return

    # Find knowledge base files relative to this file
    script_dir = Path(__file__).parent.parent.parent
    kb_files = [
        script_dir / "VISA_EXHIBIT_RAG_COMPREHENSIVE_INSTRUCTIONS.md",
        script_dir / "EXHIBIT_GENERATION_KNOWLEDGE_BASE.txt",
    ]

    try:
        rag = GeminiRAG(api_key)
        for kb_file in kb_files:
            if kb_file.exists():
                # Check if already indexed
                docs = rag.list_documents()
                if not any(d.get("display_name") == kb_file.name for d in docs):
                    rag.index_document(str(kb_file))
                    logger.info(f"Auto-indexed: {kb_file.name}")
    except Exception as e:
        logger.debug(f"Auto-indexing skipped: {e}")


# Don't auto-index on import - user should explicitly initialize
# _auto_index_knowledge_base()
