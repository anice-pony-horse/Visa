"""
File Handler V2 - ZIP Extraction and Encrypted PDF Detection
=============================================================

Fixes Issues #2 and #3:
- #2: ZIP Files Broken - Robust extraction with security checks
- #3: Encrypted PDFs Crash System - Detect and skip with warnings

Security:
- Path traversal prevention (no ../ or absolute paths in ZIP)
- Encrypted PDF detection before processing
"""

import os
import zipfile
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_zip(
    zip_path: str,
    extract_to: Optional[str] = None,
    allowed_extensions: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Safely extract ZIP files with security checks.

    Fixes Issue #2: ZIP Files Broken

    Args:
        zip_path: Path to ZIP file (can be string path or file-like object)
        extract_to: Directory to extract to (creates temp if None)
        allowed_extensions: List of allowed file extensions (default: ['.pdf'])

    Returns:
        List of dicts with path, name, size for each extracted file

    Raises:
        ValueError: For invalid/corrupted ZIP or security violations
        RuntimeError: For extraction failures
    """
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.PDF']

    extracted_files = []

    # Create temp directory if not specified
    if extract_to is None:
        extract_to = tempfile.mkdtemp(prefix='visa_exhibit_')

    try:
        # Handle both file paths and file objects
        if hasattr(zip_path, 'read'):
            # It's a file-like object (from Streamlit upload)
            temp_zip = os.path.join(extract_to, 'upload.zip')
            with open(temp_zip, 'wb') as f:
                f.write(zip_path.read())
            zip_path = temp_zip

        if not os.path.exists(zip_path):
            raise ValueError(f"ZIP file not found: {zip_path}")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # SECURITY: Check for path traversal attacks
            for member in zip_ref.namelist():
                # Check for absolute paths
                if member.startswith('/') or member.startswith('\\'):
                    raise ValueError(f"Security: Absolute path in ZIP: {member}")

                # Check for path traversal
                if '..' in member:
                    raise ValueError(f"Security: Path traversal in ZIP: {member}")

                # Check for suspicious patterns
                normalized = os.path.normpath(member)
                if normalized.startswith('..'):
                    raise ValueError(f"Security: Unsafe path in ZIP: {member}")

            # Extract all files
            zip_ref.extractall(extract_to)

            # Find files matching allowed extensions
            for root, dirs, files in os.walk(extract_to):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for file in files:
                    # Skip hidden files
                    if file.startswith('.'):
                        continue

                    # Check extension
                    ext = Path(file).suffix.lower()
                    if ext in [e.lower() for e in allowed_extensions]:
                        full_path = os.path.join(root, file)
                        extracted_files.append({
                            "path": full_path,
                            "name": file,
                            "size": os.path.getsize(full_path),
                            "relative_path": os.path.relpath(full_path, extract_to)
                        })

        logger.info(f"Extracted {len(extracted_files)} files from ZIP")
        return extracted_files

    except zipfile.BadZipFile:
        raise ValueError("Invalid or corrupted ZIP file")

    except Exception as e:
        if "Security" in str(e) or "Path" in str(e):
            raise  # Re-raise security exceptions
        raise RuntimeError(f"ZIP extraction failed: {str(e)}")


def check_pdf_encryption(pdf_path: str) -> Dict[str, Any]:
    """
    Check if PDF is encrypted/password-protected.

    Fixes Issue #3: Encrypted PDFs Crash System

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict with:
        - encrypted: bool
        - can_process: bool
        - page_count: int (if readable)
        - message: str (status/error message)
    """
    try:
        from PyPDF2 import PdfReader
        from PyPDF2.errors import FileNotDecryptedError, PdfReadError
    except ImportError:
        return {
            "encrypted": False,
            "can_process": False,
            "message": "PyPDF2 not installed"
        }

    try:
        reader = PdfReader(pdf_path)

        # Check encryption status
        if reader.is_encrypted:
            return {
                "encrypted": True,
                "can_process": False,
                "message": f"Password-protected: {os.path.basename(pdf_path)}"
            }

        # Try to access pages to verify readable
        page_count = len(reader.pages)

        # Try to read first page content to ensure not corrupted
        try:
            _ = reader.pages[0]
        except Exception:
            pass  # Some PDFs fail here but are still processable

        return {
            "encrypted": False,
            "can_process": True,
            "page_count": page_count,
            "message": f"OK: {page_count} pages"
        }

    except FileNotDecryptedError:
        return {
            "encrypted": True,
            "can_process": False,
            "message": f"Requires password: {os.path.basename(pdf_path)}"
        }

    except PdfReadError as e:
        return {
            "encrypted": False,
            "can_process": False,
            "message": f"Corrupted PDF: {str(e)[:50]}"
        }

    except Exception as e:
        return {
            "encrypted": False,
            "can_process": False,
            "message": f"Error reading PDF: {str(e)[:50]}"
        }


def filter_processable_pdfs(
    pdf_list: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Filter list of PDFs, separating processable from skipped.

    Args:
        pdf_list: List of dicts with 'path' key

    Returns:
        Tuple of (processable_list, skipped_list)
        Each item in skipped_list has 'file' and 'reason' keys
    """
    processable = []
    skipped = []

    for pdf in pdf_list:
        path = pdf.get('path', pdf.get('file_path', ''))
        name = pdf.get('name', os.path.basename(path))

        if not path or not os.path.exists(path):
            skipped.append({
                "file": name,
                "reason": "File not found"
            })
            continue

        status = check_pdf_encryption(path)

        if status["can_process"]:
            pdf["page_count"] = status.get("page_count", 0)
            processable.append(pdf)
        else:
            skipped.append({
                "file": name,
                "reason": status["message"]
            })

    logger.info(f"Filtered PDFs: {len(processable)} processable, {len(skipped)} skipped")
    return processable, skipped


def get_pdf_info(pdf_path: str) -> Dict[str, Any]:
    """
    Get detailed information about a PDF file.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict with file info, page count, encryption status, etc.
    """
    info = {
        "path": pdf_path,
        "name": os.path.basename(pdf_path),
        "size": 0,
        "page_count": 0,
        "encrypted": False,
        "can_process": False,
        "error": None
    }

    if not os.path.exists(pdf_path):
        info["error"] = "File not found"
        return info

    info["size"] = os.path.getsize(pdf_path)

    encryption_status = check_pdf_encryption(pdf_path)
    info.update({
        "encrypted": encryption_status.get("encrypted", False),
        "can_process": encryption_status.get("can_process", False),
        "page_count": encryption_status.get("page_count", 0),
        "error": encryption_status.get("message") if not encryption_status.get("can_process") else None
    })

    return info


def validate_pdf_batch(file_paths: List[str]) -> Dict[str, Any]:
    """
    Validate a batch of PDF files for processing.

    Args:
        file_paths: List of PDF file paths

    Returns:
        Dict with:
        - valid: List of valid file paths
        - invalid: List of dicts with path and error
        - total_pages: Total page count of valid files
        - total_size: Total size in bytes of valid files
    """
    valid = []
    invalid = []
    total_pages = 0
    total_size = 0

    for path in file_paths:
        info = get_pdf_info(path)

        if info["can_process"]:
            valid.append(path)
            total_pages += info["page_count"]
            total_size += info["size"]
        else:
            invalid.append({
                "path": path,
                "name": info["name"],
                "error": info.get("error", "Unknown error")
            })

    return {
        "valid": valid,
        "invalid": invalid,
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "total_pages": total_pages,
        "total_size": total_size
    }
