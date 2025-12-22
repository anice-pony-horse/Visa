"""
Intake Form Component (Feature 1)
=================================

Optional context form for AI enrichment.
ALL FIELDS ARE OPTIONAL - users can skip entirely.

Per 8 CFR 214.2(o)(2)(iv)(E):
- Direct Employment
- US Agent Functioning as Employer
- US Agent for Foreign Employer
- US Agent for Multiple Employers
"""

import streamlit as st
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class CaseContext:
    """Case context data - all fields optional"""
    visa_category: Optional[str] = None
    beneficiary_name: Optional[str] = None
    petitioner_name: Optional[str] = None
    petition_structure: Optional[str] = None
    processing_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def is_empty(self) -> bool:
        """Check if all fields are empty"""
        return all(v is None for v in asdict(self).values())


# Visa petition categories
VISA_CATEGORIES = [
    "",  # Empty option for "None selected"
    "O-1A (Extraordinary Ability - Sciences, Education, Business, Athletics)",
    "O-1B (Extraordinary Achievement - Arts, Motion Picture, Television)",
    "O-2 (Essential Support Personnel)",
    "P-1A (Internationally Recognized Athlete/Team)",
    "P-1B (Internationally Recognized Entertainment Group)",
    "P-1S (Essential Support Personnel for P-1)",
    "EB-1A (Employment-Based First Preference - Extraordinary Ability)",
    "EB-1B (Outstanding Professors and Researchers)",
    "EB-2 NIW (National Interest Waiver)",
]

# Petition structure types per 8 CFR 214.2(o)(2)(iv)(E)
PETITION_STRUCTURES = {
    "": {
        "label": "None selected",
        "description": ""
    },
    "direct_employment": {
        "label": "Direct Employment",
        "description": "U.S. employer directly employs the beneficiary with specific job offer"
    },
    "agent_as_employer": {
        "label": "US Agent Functioning as Employer",
        "description": "Agent performs employer function - manages work, wages, and conditions (8 CFR 214.2(o)(2)(iv)(E))"
    },
    "agent_for_foreign": {
        "label": "US Agent for Foreign Employer",
        "description": "Agent files on behalf of a foreign employer who authorizes the agent to act"
    },
    "agent_for_multiple": {
        "label": "US Agent for Multiple Employers",
        "description": "Agent files for beneficiary working with multiple U.S. employers (requires itinerary + contracts)"
    }
}

# Processing types
PROCESSING_TYPES = [
    "",  # Empty option
    "Regular Processing (standard timeline)",
    "Premium Processing (15 calendar days - additional USCIS fee)"
]


def _init_session_state():
    """Initialize session state for intake form"""
    if 'case_context' not in st.session_state:
        st.session_state.case_context = CaseContext()


def get_case_context() -> CaseContext:
    """Get the current case context from session state"""
    _init_session_state()
    return st.session_state.case_context


def render_intake_form() -> CaseContext:
    """
    Render the optional intake form.

    Returns:
        CaseContext: The collected case context (may be empty)
    """
    _init_session_state()

    st.markdown("""
    <div style="background-color: #e7f3ff; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4; margin-bottom: 1rem;">
        <strong>All fields are optional</strong><br>
        <small>This information helps the AI better classify your documents. You can skip this step entirely.</small>
    </div>
    """, unsafe_allow_html=True)

    # Create form layout
    col1, col2 = st.columns(2)

    with col1:
        # Visa Petition Category
        visa_category = st.selectbox(
            "Visa Petition Category",
            options=VISA_CATEGORIES,
            index=0,
            help="Select the visa type for this petition (optional)"
        )

        # Beneficiary Name
        beneficiary_name = st.text_input(
            "Beneficiary Name",
            placeholder="Full legal name of beneficiary (optional)",
            help="The person who will receive the visa benefit"
        )

    with col2:
        # Petitioner Name
        petitioner_name = st.text_input(
            "Petitioner Name",
            placeholder="Employer, Agent, or Sponsoring Organization (optional)",
            help="The entity filing the petition"
        )

        # Processing Type
        processing_type = st.selectbox(
            "Processing Type",
            options=PROCESSING_TYPES,
            index=0,
            help="Standard or premium processing (optional)"
        )

    # Petition Structure - Full width with radio buttons
    st.markdown("---")
    st.markdown("**Petition Structure Type** *(per 8 CFR 214.2(o)(2)(iv)(E))*")
    st.caption("How is this petition being filed?")

    # Create radio options
    structure_options = ["None selected"] + [
        f"{info['label']}"
        for key, info in PETITION_STRUCTURES.items()
        if key != ""
    ]

    selected_structure_label = st.radio(
        "Petition Structure",
        options=structure_options,
        label_visibility="collapsed",
        horizontal=False
    )

    # Show description for selected structure
    if selected_structure_label != "None selected":
        for key, info in PETITION_STRUCTURES.items():
            if info['label'] == selected_structure_label:
                st.info(f"📋 {info['description']}")
                break

    # Map selection back to key
    petition_structure = None
    for key, info in PETITION_STRUCTURES.items():
        if info['label'] == selected_structure_label and key != "":
            petition_structure = key
            break

    # Update session state
    context = CaseContext(
        visa_category=visa_category if visa_category else None,
        beneficiary_name=beneficiary_name if beneficiary_name else None,
        petitioner_name=petitioner_name if petitioner_name else None,
        petition_structure=petition_structure,
        processing_type=processing_type if processing_type else None
    )

    st.session_state.case_context = context

    # Show summary if any fields filled
    if not context.is_empty():
        st.markdown("---")
        with st.expander("📋 Case Context Summary", expanded=False):
            data = context.to_dict()
            for key, value in data.items():
                st.write(f"**{key.replace('_', ' ').title()}**: {value}")

    return context


def render_context_summary():
    """Render a compact summary of the case context (for other stages)"""
    context = get_case_context()

    if context.is_empty():
        return

    with st.expander("📋 Case Context", expanded=False):
        data = context.to_dict()
        cols = st.columns(len(data))
        for col, (key, value) in zip(cols, data.items()):
            with col:
                st.caption(key.replace('_', ' ').title())
                st.write(value if value else "-")
