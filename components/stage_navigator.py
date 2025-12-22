"""
Stage Navigator Component (Feature 3)
=====================================

6-stage workflow navigation:
1. Context (optional) - Case information
2. Upload - PDFs, URLs, Google Drive
3. Classify - AI auto-categorization
4. Review - Manual reorder + text commands
5. Generate - Background processing
6. Complete - Download, email, share link
"""

import streamlit as st
from dataclasses import dataclass
from typing import List, Optional, Callable


@dataclass
class Stage:
    """Stage definition"""
    id: int
    name: str
    icon: str
    description: str
    can_skip: bool = False


# Define the 6 stages
STAGES: List[Stage] = [
    Stage(0, "Context", "📋", "Case information (optional)", can_skip=True),
    Stage(1, "Upload", "📁", "Upload documents"),
    Stage(2, "Classify", "🤖", "AI classification"),
    Stage(3, "Review", "✏️", "Review & reorder"),
    Stage(4, "Generate", "⚙️", "Generate exhibits"),
    Stage(5, "Complete", "✅", "Download & share"),
]


class StageNavigator:
    """Manages stage navigation state and UI"""

    def __init__(self):
        """Initialize stage navigator"""
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state variables"""
        if 'current_stage' not in st.session_state:
            st.session_state.current_stage = 0
        if 'stage_history' not in st.session_state:
            st.session_state.stage_history = [0]
        if 'stage_data' not in st.session_state:
            st.session_state.stage_data = {}

    @property
    def current_stage(self) -> int:
        """Get current stage index"""
        return st.session_state.current_stage

    @property
    def current_stage_info(self) -> Stage:
        """Get current stage info"""
        return STAGES[self.current_stage]

    def go_to_stage(self, stage_id: int):
        """Navigate to a specific stage"""
        if 0 <= stage_id < len(STAGES):
            st.session_state.current_stage = stage_id
            st.session_state.stage_history.append(stage_id)

    def next_stage(self):
        """Move to next stage"""
        if self.current_stage < len(STAGES) - 1:
            self.go_to_stage(self.current_stage + 1)

    def prev_stage(self):
        """Move to previous stage"""
        if self.current_stage > 0:
            self.go_to_stage(self.current_stage - 1)

    def skip_stage(self):
        """Skip current stage (if allowed)"""
        if STAGES[self.current_stage].can_skip:
            self.next_stage()

    def reset(self):
        """Reset to first stage"""
        st.session_state.current_stage = 0
        st.session_state.stage_history = [0]
        st.session_state.stage_data = {}

    def save_stage_data(self, key: str, value):
        """Save data for current stage"""
        stage_key = f"stage_{self.current_stage}_{key}"
        st.session_state.stage_data[stage_key] = value

    def get_stage_data(self, stage_id: int, key: str, default=None):
        """Get data from a specific stage"""
        stage_key = f"stage_{stage_id}_{key}"
        return st.session_state.stage_data.get(stage_key, default)

    def render_progress_bar(self):
        """Render the stage progress bar"""
        progress = (self.current_stage + 1) / len(STAGES)

        # Progress bar
        st.progress(progress)

        # Stage indicators
        cols = st.columns(len(STAGES))
        for i, (col, stage) in enumerate(zip(cols, STAGES)):
            with col:
                if i < self.current_stage:
                    # Completed stage
                    st.markdown(f"<div style='text-align:center; color:#28a745;'>{stage.icon}<br><small>✓ {stage.name}</small></div>", unsafe_allow_html=True)
                elif i == self.current_stage:
                    # Current stage
                    st.markdown(f"<div style='text-align:center; color:#1f77b4; font-weight:bold;'>{stage.icon}<br><small>{stage.name}</small></div>", unsafe_allow_html=True)
                else:
                    # Future stage
                    st.markdown(f"<div style='text-align:center; color:#ccc;'>{stage.icon}<br><small>{stage.name}</small></div>", unsafe_allow_html=True)

    def render_navigation_buttons(
        self,
        on_next: Optional[Callable] = None,
        on_back: Optional[Callable] = None,
        on_skip: Optional[Callable] = None,
        next_label: str = "Continue",
        next_disabled: bool = False
    ):
        """Render navigation buttons"""
        current = STAGES[self.current_stage]

        col1, col2, col3 = st.columns([1, 1, 1])

        # Back button
        with col1:
            if self.current_stage > 0:
                if st.button("← Back", use_container_width=True):
                    if on_back:
                        on_back()
                    self.prev_stage()
                    st.rerun()

        # Skip button (only for skippable stages)
        with col2:
            if current.can_skip:
                if st.button("Skip →", use_container_width=True):
                    if on_skip:
                        on_skip()
                    self.skip_stage()
                    st.rerun()

        # Next button
        with col3:
            if self.current_stage < len(STAGES) - 1:
                if st.button(
                    f"{next_label} →",
                    type="primary",
                    use_container_width=True,
                    disabled=next_disabled
                ):
                    if on_next:
                        on_next()
                    self.next_stage()
                    st.rerun()
            elif self.current_stage == len(STAGES) - 1:
                # Last stage - Start New Case button
                if st.button("🔄 Start New Case", type="primary", use_container_width=True):
                    self.reset()
                    # Clear all session state
                    for key in list(st.session_state.keys()):
                        if key not in ['current_stage', 'stage_history', 'stage_data']:
                            del st.session_state[key]
                    st.rerun()


def render_stage_header(navigator: StageNavigator):
    """Render the stage header with progress bar"""
    st.markdown("---")
    navigator.render_progress_bar()

    current = navigator.current_stage_info
    st.markdown(f"### {current.icon} Stage {current.id + 1}: {current.name}")
    st.caption(current.description)
    st.markdown("---")
