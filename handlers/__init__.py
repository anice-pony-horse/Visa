"""
Handlers Package
================
Core handlers for the Visa Exhibit Generator V2.

This package contains:
- compress_handler: PDF compression with Ghostscript/PyMuPDF
- file_handler: ZIP extraction, encrypted PDF detection
- pdf_handler: PDF manipulation, numbering, merging
- timeout_handler: Graceful timeout with partial output
- state_manager: Session state persistence
"""

from .compress_handler import USCISPDFCompressor, compress_pdf_batch, verify_ghostscript
from .file_handler import extract_zip, check_pdf_encryption, filter_processable_pdfs
from .timeout_handler import TimeoutManager, process_with_timeout
from .state_manager import init_session_state, save_form_data, StateManager

__all__ = [
    'USCISPDFCompressor',
    'compress_pdf_batch',
    'verify_ghostscript',
    'extract_zip',
    'check_pdf_encryption',
    'filter_processable_pdfs',
    'TimeoutManager',
    'process_with_timeout',
    'init_session_state',
    'save_form_data',
    'StateManager',
]
