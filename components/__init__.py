"""
Exhibit Maker V2.0 Components
=============================

Feature modules for the 6-stage workflow:
- Stage 1: intake_form (optional context)
- Stage 2: url_manager (URL drag-drop)
- Stage 3: ai_classifier (AI classification)
- Stage 4: exhibit_editor (manual reorder)
- Stage 5: background_processor (async processing)
- Stage 6: link_generator, email_sender (delivery)
"""

from .stage_navigator import StageNavigator, STAGES
from .intake_form import render_intake_form, get_case_context
from .url_manager import URLManager, render_url_manager
from .ai_classifier import AIClassifier, ClassificationResult
from .exhibit_editor import ExhibitEditor, render_exhibit_editor
from .background_processor import BackgroundProcessor, ProcessingStatus
from .email_sender import EmailSender, send_completion_email
from .link_generator import LinkGenerator, generate_shareable_link

__all__ = [
    'StageNavigator',
    'STAGES',
    'render_intake_form',
    'get_case_context',
    'URLManager',
    'render_url_manager',
    'AIClassifier',
    'ClassificationResult',
    'ExhibitEditor',
    'render_exhibit_editor',
    'BackgroundProcessor',
    'ProcessingStatus',
    'EmailSender',
    'send_completion_email',
    'LinkGenerator',
    'generate_shareable_link',
]
