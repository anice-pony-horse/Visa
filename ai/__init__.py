"""
AI Package
==========
AI-powered features for the Visa Exhibit Generator V2.

This package contains:
- gemini_rag: Gemini File Search API for RAG-powered knowledge
- exhibit_classifier: Document classification using Claude
- auto_orderer: RAG-based exhibit ordering
- chat_parser: Natural language arrangement instructions
"""

from .gemini_rag import GeminiRAG, create_visa_knowledge_store, query_visa_knowledge
from .exhibit_classifier import ExhibitClassifier, classify_document
from .auto_orderer import AutoOrderer, get_criterion_order

__all__ = [
    'GeminiRAG',
    'create_visa_knowledge_store',
    'query_visa_knowledge',
    'ExhibitClassifier',
    'classify_document',
    'AutoOrderer',
    'get_criterion_order',
]
