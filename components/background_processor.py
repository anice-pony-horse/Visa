"""
Background Processor Component (Feature 7)
============================================

Async processing with progress tracking.
- Threading for background processing
- Real-time progress bar
- Step-by-step status updates
- Auto-advance on completion
"""

import streamlit as st
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import threading
import time
import traceback
from datetime import datetime


class ProcessingStatus(Enum):
    """Processing status enum"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class ProcessingStep:
    """Represents a processing step"""
    name: str
    description: str
    status: str = "pending"  # pending, running, completed, error
    progress: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class ProcessingState:
    """Overall processing state"""
    status: ProcessingStatus = ProcessingStatus.IDLE
    current_step: int = 0
    steps: List[ProcessingStep] = field(default_factory=list)
    overall_progress: float = 0.0
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'current_step': self.current_step,
            'steps': [
                {
                    'name': s.name,
                    'description': s.description,
                    'status': s.status,
                    'progress': s.progress,
                    'error_message': s.error_message,
                }
                for s in self.steps
            ],
            'overall_progress': self.overall_progress,
            'error_message': self.error_message,
            'result': self.result,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
        }


# Default processing steps
DEFAULT_STEPS = [
    ProcessingStep("extract", "Extracting documents..."),
    ProcessingStep("compress", "Applying compression..."),
    ProcessingStep("number", "Adding exhibit numbers..."),
    ProcessingStep("toc", "Generating Table of Contents..."),
    ProcessingStep("merge", "Merging exhibits..."),
    ProcessingStep("finalize", "Finalizing PDF..."),
]


class BackgroundProcessor:
    """Background processing manager"""

    def __init__(self):
        """Initialize processor"""
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state"""
        if 'processing_state' not in st.session_state:
            st.session_state.processing_state = ProcessingState(
                steps=[ProcessingStep(s.name, s.description) for s in DEFAULT_STEPS]
            )
        if 'processing_thread' not in st.session_state:
            st.session_state.processing_thread = None

    @property
    def state(self) -> ProcessingState:
        """Get current processing state"""
        # Ensure processing_state exists before accessing
        if 'processing_state' not in st.session_state:
            self._init_session_state()
        return st.session_state.processing_state

    @property
    def is_running(self) -> bool:
        """Check if processing is running"""
        return self.state.status == ProcessingStatus.RUNNING

    @property
    def is_complete(self) -> bool:
        """Check if processing is complete"""
        return self.state.status == ProcessingStatus.COMPLETED

    @property
    def has_error(self) -> bool:
        """Check if processing has error"""
        return self.state.status == ProcessingStatus.ERROR

    def reset(self):
        """Reset processing state"""
        st.session_state.processing_state = ProcessingState(
            steps=[ProcessingStep(s.name, s.description) for s in DEFAULT_STEPS]
        )

    def start_processing(
        self,
        process_func: Callable[['BackgroundProcessor'], Dict[str, Any]],
        custom_steps: Optional[List[ProcessingStep]] = None
    ):
        """
        Start background processing.

        Args:
            process_func: Function to execute (receives processor instance)
            custom_steps: Optional custom processing steps
        """
        if self.is_running:
            return

        # Reset state
        if custom_steps:
            st.session_state.processing_state = ProcessingState(steps=custom_steps)
        else:
            self.reset()

        state = self.state
        state.status = ProcessingStatus.RUNNING
        state.started_at = datetime.now().isoformat()

        # Start processing in background thread
        def run_process():
            try:
                result = process_func(self)
                state.result = result
                state.status = ProcessingStatus.COMPLETED
                state.completed_at = datetime.now().isoformat()
            except Exception as e:
                state.error_message = str(e)
                state.status = ProcessingStatus.ERROR
                logger.error(f"Processing error: {traceback.format_exc()}")

        thread = threading.Thread(target=run_process, daemon=True)
        st.session_state.processing_thread = thread
        thread.start()

    def update_step(
        self,
        step_name: str,
        status: str = "running",
        progress: float = 0.0,
        error_message: Optional[str] = None
    ):
        """Update a processing step"""
        state = self.state

        for i, step in enumerate(state.steps):
            if step.name == step_name:
                step.status = status
                step.progress = progress
                step.error_message = error_message

                if status == "running":
                    step.started_at = datetime.now().isoformat()
                    state.current_step = i
                elif status == "completed":
                    step.completed_at = datetime.now().isoformat()
                    step.progress = 100.0

                break

        # Update overall progress
        completed_steps = sum(1 for s in state.steps if s.status == "completed")
        current_progress = sum(s.progress for s in state.steps if s.status == "running") / 100
        state.overall_progress = (completed_steps + current_progress) / len(state.steps)

    def complete_step(self, step_name: str):
        """Mark a step as completed"""
        self.update_step(step_name, status="completed", progress=100.0)

    def set_step_progress(self, step_name: str, progress: float):
        """Set progress for current step"""
        self.update_step(step_name, status="running", progress=progress)

    def cancel(self):
        """Cancel processing"""
        self.state.status = ProcessingStatus.CANCELLED


def render_processing_ui() -> Optional[Dict[str, Any]]:
    """
    Render the processing progress UI.

    Returns:
        Processing result when complete, None otherwise
    """
    processor = BackgroundProcessor()
    state = processor.state

    st.subheader("⚙️ Generating Exhibits")

    # Overall progress bar
    st.progress(state.overall_progress)

    # Status message
    if state.status == ProcessingStatus.RUNNING:
        current_step = state.steps[state.current_step] if state.current_step < len(state.steps) else None
        if current_step:
            st.info(f"⏳ {current_step.description}")
    elif state.status == ProcessingStatus.COMPLETED:
        st.success("✅ Processing complete!")
    elif state.status == ProcessingStatus.ERROR:
        st.error(f"❌ Error: {state.error_message}")
    elif state.status == ProcessingStatus.CANCELLED:
        st.warning("⚠️ Processing cancelled")

    # Step-by-step status
    st.markdown("---")

    for step in state.steps:
        col1, col2, col3 = st.columns([0.5, 3, 0.5])

        with col1:
            if step.status == "completed":
                st.markdown("✅")
            elif step.status == "running":
                st.markdown("⏳")
            elif step.status == "error":
                st.markdown("❌")
            else:
                st.markdown("⬜")

        with col2:
            st.write(step.description)
            if step.status == "running" and step.progress > 0:
                st.progress(step.progress / 100)

        with col3:
            if step.status == "completed":
                st.caption("Done")
            elif step.status == "running":
                st.caption(f"{step.progress:.0f}%")

    # Cancel button (if running)
    if state.status == ProcessingStatus.RUNNING:
        st.markdown("---")
        if st.button("Cancel", type="secondary"):
            processor.cancel()
            st.rerun()

        # Auto-refresh while running
        time.sleep(0.5)
        st.rerun()

    # Return result if complete
    if state.status == ProcessingStatus.COMPLETED:
        return state.result

    return None


def get_processor() -> BackgroundProcessor:
    """Get the background processor instance"""
    return BackgroundProcessor()


def create_exhibit_processor(
    files: List[Any],
    options: Dict[str, Any]
) -> Callable[[BackgroundProcessor], Dict[str, Any]]:
    """
    Create a processing function for exhibit generation.

    Args:
        files: List of files to process
        options: Processing options

    Returns:
        Callable that performs the processing
    """
    def process(processor: BackgroundProcessor) -> Dict[str, Any]:
        """Process exhibits"""
        result = {
            'exhibits': [],
            'total_pages': 0,
            'original_size': 0,
            'compressed_size': 0,
            'output_file': None
        }

        # Step 1: Extract
        processor.update_step("extract", "running")
        for i, file in enumerate(files):
            # Simulate extraction
            time.sleep(0.1)
            processor.set_step_progress("extract", (i + 1) / len(files) * 100)
        processor.complete_step("extract")

        # Step 2: Compress
        if options.get('enable_compression', True):
            processor.update_step("compress", "running")
            for i in range(len(files)):
                time.sleep(0.1)
                processor.set_step_progress("compress", (i + 1) / len(files) * 100)
            processor.complete_step("compress")
        else:
            processor.complete_step("compress")

        # Step 3: Number
        processor.update_step("number", "running")
        for i in range(len(files)):
            time.sleep(0.05)
            processor.set_step_progress("number", (i + 1) / len(files) * 100)
        processor.complete_step("number")

        # Step 4: TOC
        if options.get('add_toc', True):
            processor.update_step("toc", "running")
            time.sleep(0.2)
            processor.complete_step("toc")
        else:
            processor.complete_step("toc")

        # Step 5: Merge
        if options.get('merge_pdfs', True):
            processor.update_step("merge", "running")
            time.sleep(0.3)
            processor.complete_step("merge")
        else:
            processor.complete_step("merge")

        # Step 6: Finalize
        processor.update_step("finalize", "running")
        time.sleep(0.2)
        processor.complete_step("finalize")

        return result

    return process
