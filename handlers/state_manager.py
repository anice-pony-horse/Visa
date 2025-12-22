"""
State Manager V2 - Persistent Session State
============================================

Fixes Issue #6: Input Field Data Disappears

Key improvements:
- All form data persists through reruns
- Explicit state initialization with defaults
- State validation and recovery
- Export/import state for session recovery
"""

import streamlit as st
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CaseContext:
    """Case context data structure"""
    beneficiary_name: str = ""
    petitioner_name: str = ""
    visa_type: str = "O-1A"
    processing_type: str = "Regular"
    petition_structure: str = "Direct Employment"
    field_of_expertise: str = ""
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ExhibitItem:
    """Single exhibit data structure"""
    id: str = ""
    number: str = ""
    name: str = ""
    filename: str = ""
    file_path: str = ""
    page_count: int = 0
    category: str = ""
    criterion: str = ""
    classification_method: str = "manual"
    confidence: float = 0.0
    thumbnail: Optional[str] = None


# Default session state values
DEFAULT_STATE = {
    # Case context
    "beneficiary_name": "",
    "petitioner_name": "",
    "visa_type": "O-1A",
    "processing_type": "Regular",
    "petition_structure": "Direct Employment",
    "field_of_expertise": "",
    "notes": "",

    # File data
    "uploaded_files": [],
    "zip_files": [],
    "url_list": [],
    "exhibit_order": [],
    "processed_files": [],
    "classifications": [],

    # UI state
    "current_stage": 0,
    "generation_complete": False,
    "exhibits_generated": False,
    "last_error": None,

    # Output data
    "output_file": None,
    "exhibit_list": [],
    "compression_stats": None,

    # Processing state
    "processing_status": "idle",
    "processing_progress": 0,
    "processing_message": "",

    # Settings
    "enable_compression": True,
    "quality_preset": "high",
    "enable_ai": True,
    "add_toc": True,
    "add_archive": False,
    "merge_pdfs": True,
    "numbering_style": "letters",
}


def init_session_state(force_reset: bool = False):
    """
    Initialize all session state variables with defaults.

    Fixes Issue #6: Input Field Data Disappears

    Args:
        force_reset: If True, reset all values to defaults
    """
    if force_reset:
        for key in list(st.session_state.keys()):
            del st.session_state[key]

    for key, default_value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def save_form_data(key: str, value: Any):
    """
    Save a form field value to session state.

    Args:
        key: State key
        value: Value to save
    """
    if key in DEFAULT_STATE:
        st.session_state[key] = value
    else:
        logger.warning(f"Saving unknown state key: {key}")
        st.session_state[key] = value


def get_state(key: str, default: Any = None) -> Any:
    """
    Get a value from session state.

    Args:
        key: State key
        default: Default if not found

    Returns:
        Value or default
    """
    return st.session_state.get(key, default)


def set_state(key: str, value: Any):
    """
    Set a value in session state.

    Args:
        key: State key
        value: Value to set
    """
    st.session_state[key] = value


class StateManager:
    """
    Manages session state with validation and persistence.
    """

    @staticmethod
    def initialize():
        """Initialize session state with all defaults."""
        init_session_state()

    @staticmethod
    def reset():
        """Reset all state to defaults."""
        init_session_state(force_reset=True)

    @staticmethod
    def get_case_context() -> CaseContext:
        """Get case context from session state."""
        return CaseContext(
            beneficiary_name=st.session_state.get("beneficiary_name", ""),
            petitioner_name=st.session_state.get("petitioner_name", ""),
            visa_type=st.session_state.get("visa_type", "O-1A"),
            processing_type=st.session_state.get("processing_type", "Regular"),
            petition_structure=st.session_state.get("petition_structure", "Direct Employment"),
            field_of_expertise=st.session_state.get("field_of_expertise", ""),
            notes=st.session_state.get("notes", ""),
        )

    @staticmethod
    def set_case_context(context: CaseContext):
        """Save case context to session state."""
        st.session_state["beneficiary_name"] = context.beneficiary_name
        st.session_state["petitioner_name"] = context.petitioner_name
        st.session_state["visa_type"] = context.visa_type
        st.session_state["processing_type"] = context.processing_type
        st.session_state["petition_structure"] = context.petition_structure
        st.session_state["field_of_expertise"] = context.field_of_expertise
        st.session_state["notes"] = context.notes

    @staticmethod
    def get_exhibits() -> List[Dict]:
        """Get exhibit list from session state."""
        return st.session_state.get("exhibit_order", [])

    @staticmethod
    def set_exhibits(exhibits: List[Dict]):
        """Save exhibit list to session state."""
        st.session_state["exhibit_order"] = exhibits

    @staticmethod
    def get_stage() -> int:
        """Get current workflow stage."""
        return st.session_state.get("current_stage", 0)

    @staticmethod
    def set_stage(stage: int):
        """Set current workflow stage."""
        st.session_state["current_stage"] = stage

    @staticmethod
    def next_stage():
        """Advance to next stage."""
        current = st.session_state.get("current_stage", 0)
        st.session_state["current_stage"] = current + 1

    @staticmethod
    def prev_stage():
        """Go to previous stage."""
        current = st.session_state.get("current_stage", 0)
        st.session_state["current_stage"] = max(0, current - 1)

    @staticmethod
    def export_state() -> str:
        """
        Export current state as JSON string.

        Returns:
            JSON string of exportable state
        """
        exportable_keys = [
            "beneficiary_name", "petitioner_name", "visa_type",
            "processing_type", "petition_structure", "field_of_expertise",
            "notes", "exhibit_order", "classifications", "current_stage"
        ]

        export_data = {}
        for key in exportable_keys:
            value = st.session_state.get(key)
            if value is not None:
                # Handle non-serializable types
                try:
                    json.dumps(value)
                    export_data[key] = value
                except (TypeError, ValueError):
                    export_data[key] = str(value)

        export_data["exported_at"] = datetime.now().isoformat()
        return json.dumps(export_data, indent=2)

    @staticmethod
    def import_state(json_string: str) -> bool:
        """
        Import state from JSON string.

        Args:
            json_string: JSON state data

        Returns:
            True if import successful
        """
        try:
            data = json.loads(json_string)

            # Validate it has expected structure
            if not isinstance(data, dict):
                return False

            # Import only known keys
            for key in DEFAULT_STATE.keys():
                if key in data:
                    st.session_state[key] = data[key]

            return True

        except json.JSONDecodeError:
            logger.error("Failed to parse state JSON")
            return False
        except Exception as e:
            logger.error(f"Failed to import state: {e}")
            return False

    @staticmethod
    def validate_state() -> Dict[str, Any]:
        """
        Validate current state and fix any issues.

        Returns:
            Dict with validation results
        """
        issues = []
        fixed = []

        # Check all required keys exist
        for key, default in DEFAULT_STATE.items():
            if key not in st.session_state:
                st.session_state[key] = default
                fixed.append(f"Initialized missing key: {key}")

        # Validate visa_type
        valid_visa_types = ["O-1A", "O-1B", "O-2", "P-1A", "P-1B", "P-1S", "EB-1A", "EB-1B", "EB-2 NIW"]
        if st.session_state.get("visa_type") not in valid_visa_types:
            st.session_state["visa_type"] = "O-1A"
            fixed.append("Reset invalid visa_type to O-1A")

        # Validate stage
        if not isinstance(st.session_state.get("current_stage"), int):
            st.session_state["current_stage"] = 0
            fixed.append("Reset invalid stage to 0")

        if st.session_state["current_stage"] < 0 or st.session_state["current_stage"] > 5:
            st.session_state["current_stage"] = 0
            fixed.append("Reset out-of-range stage to 0")

        # Validate lists are lists
        list_keys = ["uploaded_files", "zip_files", "url_list", "exhibit_order",
                     "processed_files", "classifications", "exhibit_list"]
        for key in list_keys:
            if not isinstance(st.session_state.get(key), list):
                st.session_state[key] = []
                fixed.append(f"Reset {key} to empty list")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "fixed": fixed
        }


# Streamlit input helpers that auto-persist to session state
def persistent_text_input(
    label: str,
    key: str,
    help: Optional[str] = None,
    placeholder: str = ""
) -> str:
    """
    Text input that automatically persists to session state.

    Args:
        label: Input label
        key: Session state key
        help: Help text
        placeholder: Placeholder text

    Returns:
        Current value
    """
    init_session_state()  # Ensure state exists

    value = st.text_input(
        label,
        value=st.session_state.get(key, ""),
        key=f"{key}_input",
        help=help,
        placeholder=placeholder
    )

    # Auto-persist to session state
    st.session_state[key] = value
    return value


def persistent_selectbox(
    label: str,
    key: str,
    options: List[str],
    help: Optional[str] = None
) -> str:
    """
    Selectbox that automatically persists to session state.
    """
    init_session_state()

    current_value = st.session_state.get(key, options[0] if options else "")
    index = options.index(current_value) if current_value in options else 0

    value = st.selectbox(
        label,
        options=options,
        index=index,
        key=f"{key}_input",
        help=help
    )

    st.session_state[key] = value
    return value


def persistent_text_area(
    label: str,
    key: str,
    help: Optional[str] = None,
    height: int = 100
) -> str:
    """
    Text area that automatically persists to session state.
    """
    init_session_state()

    value = st.text_area(
        label,
        value=st.session_state.get(key, ""),
        key=f"{key}_input",
        help=help,
        height=height
    )

    st.session_state[key] = value
    return value
