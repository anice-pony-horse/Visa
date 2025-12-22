"""
Templates Package
=================
Professional DOCX template generation for visa petitions.

This package generates law-firm quality documents:
- Cover letters
- Legal briefs / petition letters
- Table of contents
- Comparable evidence explanation letters
- Filing instructions (DIY mode)

CRITICAL: All output is clean professional prose.
NO MARKDOWN ARTIFACTS (**, ##, -, *, etc.)
"""

from .docx_engine import (
    DOCXTemplateEngine,
    generate_cover_letter,
    generate_legal_brief,
    generate_toc,
    generate_ce_letter,
    generate_filing_instructions
)

__all__ = [
    'DOCXTemplateEngine',
    'generate_cover_letter',
    'generate_legal_brief',
    'generate_toc',
    'generate_ce_letter',
    'generate_filing_instructions'
]
