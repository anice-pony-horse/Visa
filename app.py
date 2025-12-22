"""
Visa Exhibit Generator V2.0
===========================

Professional exhibit package generator for visa petitions.
Features 6-stage workflow with AI classification.0

Stages:
1. Context (optional) - Case information
2. Upload - PDFs, URLs, Google Drive
3. Classify - AI auto-categorization
4. Review - Manual reorder + text commands
5. Generate - Background processing
6. Complete - Download, email, share link

EXHIBIT ORGANIZATION REFERENCE:
../VISA_EXHIBIT_RAG_COMPREHENSIVE_INSTRUCTIONS.md
"""

import streamlit as st
import streamlit.components.v1 as components
import os
import io
import tempfile
from streamlit.components.v1 import html
from pathlib import Path
from typing import List, Dict, Optional, Any
import zipfile
from datetime import datetime
import shutil

# Import our modules
from pdf_handler import PDFHandler
from exhibit_processor import ExhibitProcessor
from google_drive import GoogleDriveHandler
from archive_handler import ArchiveHandler

# Import V2 components
from components.stage_navigator import StageNavigator, STAGES, render_stage_header
from components.intake_form import render_intake_form, get_case_context, render_context_summary
from components.url_manager import render_url_manager, get_url_list, URLManager
from components.ai_classifier import (
    AIClassifier, ClassificationResult,
    render_classification_ui, get_classifications, save_classifications
)
from components.exhibit_editor import (
    render_exhibit_editor, get_exhibits, set_exhibits_from_classifications
)
from components.background_processor import (
    BackgroundProcessor, render_processing_ui, get_processor
)
from components.thumbnail_grid import render_exhibit_preview
from components.email_sender import render_email_form
from components.link_generator import render_link_generator

# Import template engine for cover letters
from templates.docx_engine import DOCXTemplateEngine
from components.thumbnail_grid import generate_thumbnail

# Check if compression is available
try:
    from compress_handler import USCISPDFCompressor, compress_pdf_batch
    COMPRESSION_AVAILABLE = True
except ImportError:
    COMPRESSION_AVAILABLE = False


# Page config
st.set_page_config(
    page_title="Visa Exhibit Generator V2",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 1rem;
    }
    .version-badge {
        background: #28a745;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
        display: inline-block;
    }
    .feature-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .stat-card {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: white;
        border: 1px solid #ddd;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
    .stage-container {
        padding: 1.5rem;
        background: #fafafa;
        border-radius: 0.5rem;
        min-height: 400px;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'exhibits_generated': False,
        'compression_stats': None,
        'exhibit_list': [],
        'uploaded_files': [],
        'file_paths': [],
        'output_file': None,
        'processing_complete': False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def delete_file(idx):
    print("🎀🎀🎀")
    if 0 <= idx < len(st.session_state.uploaded_files):
        st.session_state.uploaded_files.pop(idx)
        if idx < len(st.session_state.uploaded_meta):
            st.session_state.uploaded_meta.pop(idx)
        # Adjust preview index if necessary
        if st.session_state.get('preview_file_index') == idx:
            st.session_state.preview_file_index = None
        elif st.session_state.get('preview_file_index', -1) > idx:
            st.session_state.preview_file_index -= 1
        st.rerun()

def rotate_file(idx):
    print("🎀🎀🎀")
    if 0 <= idx < len(st.session_state.uploaded_meta):
        meta = st.session_state.uploaded_meta[idx]
        current_rotation = meta.get('rotation', 0)
        meta['rotation'] = (current_rotation + 90) % 360
        st.rerun()

def duplicate_file(idx):
    print("🎀🎀🎀")
    if 0 <= idx < len(st.session_state.uploaded_files):
        original_file = st.session_state.uploaded_files[idx]
        original_meta = st.session_state.uploaded_meta[idx] if idx < len(st.session_state.uploaded_meta) else {}
        
        # Create a copy of the file in memory
        original_file.seek(0)
        content = original_file.read()
        original_file.seek(0) # Reset pointer
        
        new_file = io.BytesIO(content)
        new_file.name = f"{original_file.name}"
        new_file.size = len(content)
        
        # Copy metadata
        new_meta = original_meta.copy()
        new_meta['name'] = new_file.name
        
        # Insert after the original
        st.session_state.uploaded_files.insert(idx + 1, new_file)
        st.session_state.uploaded_meta.insert(idx + 1, new_meta)
        st.rerun()


def process_bridge_command():
    """Callback to handle bridge commands immediately"""
    if st.session_state.get("action_command"):
        cmd = st.session_state.action_command
        # Clear immediately
        st.session_state.action_command = ""
        
        parts = cmd.split(":")
        if len(parts) == 2:
            action, idx_str = parts
            try:
                idx = int(idx_str)
                if action == "delete":
                    delete_file(idx)
                elif action == "rotate":
                    rotate_file(idx)
                elif action == "duplicate":
                    duplicate_file(idx)
                elif action == "preview":
                    if st.session_state.get('preview_file_index') == idx:
                        st.session_state.preview_file_index = None
                    else:
                        st.session_state.preview_file_index = idx
                    # Force rerun if not already triggered by file ops
                    st.rerun()
            except ValueError:
                pass


def render_sidebar():
    """Render sidebar configuration"""
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Visa type selection
        visa_type = st.selectbox(
            "Visa Type",
            ["O-1A", "O-1B", "O-2", "P-1A", "P-1B", "P-1S", "EB-1A", "EB-1B", "EB-2 NIW"],
            help="Select the visa category for your petition"
        )

        # Exhibit numbering style
        numbering_style = st.selectbox(
            "Exhibit Numbering",
            ["Letters (A, B, C...)", "Numbers (1, 2, 3...)", "Roman (I, II, III...)"],
            help="How to number your exhibits"
        )

        # Convert numbering style to code
        numbering_map = {
            "Letters (A, B, C...)": "letters",
            "Numbers (1, 2, 3...)": "numbers",
            "Roman (I, II, III...)": "roman"
        }
        numbering_code = numbering_map[numbering_style]

        st.divider()

        # Compression settings
        st.header("🗜️ PDF Compression")

        if not COMPRESSION_AVAILABLE:
            st.warning("⚠️ Compression not available. Install PyMuPDF.")
            enable_compression = False
            quality_code = "high"
            smallpdf_key = None
        else:
            enable_compression = st.checkbox(
                "Enable PDF Compression",
                value=True,
                help="Compress PDFs to reduce file size (50-75% reduction)"
            )

            if enable_compression:
                quality_preset = st.selectbox(
                    "Compression Quality",
                    ["High Quality (USCIS Recommended)", "Balanced", "Maximum Compression"]
                )
                quality_map = {
                    "High Quality (USCIS Recommended)": "high",
                    "Balanced": "balanced",
                    "Maximum Compression": "maximum"
                }
                quality_code = quality_map[quality_preset]

                with st.expander("🔑 SmallPDF API Key (Optional)"):
                    smallpdf_key = st.text_input("SmallPDF API Key", type="password")
            else:
                quality_code = "high"
                smallpdf_key = None

        st.divider()

        # AI Classification settings
        st.header("🤖 AI Classification")

        enable_ai = st.checkbox(
            "Enable AI Classification",
            value=True,
            help="Use Claude API to auto-classify documents"
        )

        if enable_ai:
            with st.expander("🔑 Anthropic API Key"):
                anthropic_key = st.text_input(
                    "API Key",
                    type="password",
                    help="Get key at console.anthropic.com"
                )
                if anthropic_key:
                    st.session_state['anthropic_api_key'] = anthropic_key
                    st.success("✓ API key set")
                else:
                    st.info("Using rule-based classification")
        else:
            st.session_state['anthropic_api_key'] = None

        st.divider()

        # Output options
        st.header("📋 Options")

        add_toc = st.checkbox("Generate Table of Contents", value=True)
        add_archive = st.checkbox("Archive URLs (archive.org)", value=False)
        merge_pdfs = st.checkbox("Merge into single PDF", value=True)
        add_cover_letter = st.checkbox("Generate Cover Letter", value=True)
        add_filing_instructions = st.checkbox("Generate Filing Instructions (DIY)", value=False)
        include_full_text_images = st.checkbox("Include full extracted text & images in package", value=False,
                              help="Append a readable transcription and extracted images for each exhibit")

        st.divider()

        # Documentation
        with st.expander("📚 Help"):
            st.markdown("""
            **6-Stage Workflow:**
            1. **Context** - Optional case info
            2. **Upload** - Add documents
            3. **Classify** - AI categorization
            4. **Review** - Reorder exhibits
            5. **Generate** - Create package
            6. **Complete** - Download & share

            **Supported Visa Types:**
            O-1A, O-1B, O-2, P-1A, P-1B, P-1S, EB-1A, EB-1B, EB-2 NIW
            """)

    return {
        'visa_type': visa_type,
        'numbering_style': numbering_code,
        'enable_compression': enable_compression,
        'quality_preset': quality_code,
        'smallpdf_api_key': smallpdf_key if enable_compression else None,
        'enable_ai': enable_ai,
        'add_toc': add_toc,
        'add_archive': add_archive,
        'merge_pdfs': merge_pdfs,
        'add_cover_letter': add_cover_letter,
            'add_filing_instructions': add_filing_instructions,
            'include_full_text_images': include_full_text_images,
    }


def render_stage_1_context(navigator: StageNavigator):
    """Stage 1: Optional Context Form"""
    st.markdown('<div class="stage-container">', unsafe_allow_html=True)

    context = render_intake_form()

    st.markdown('</div>', unsafe_allow_html=True)

    # Navigation
    def on_next():
        # Context is saved automatically
        pass

    navigator.render_navigation_buttons(
        on_next=on_next,
        next_label="Continue to Upload"
    )


def render_stage_2_upload(navigator: StageNavigator, config: Dict):
    """Stage 2: Document Upload"""
    st.markdown('<div class="stage-container">', unsafe_allow_html=True)

    # Show context summary if provided
    render_context_summary()

    # Upload tabs
    tab1, tab2, tab3 = st.tabs(["📁 Upload Files", "📎 URL Documents", "☁️ Google Drive"])

    with tab1:
        st.subheader("Upload PDF Files")

        upload_method = st.radio(
            "Upload Method",
            ["Individual PDFs", "ZIP Archive"],
            horizontal=True
        )

        if upload_method == "Individual PDFs":
            current = st.session_state.get("uploaded_files", [])

            if not current:
                # Hidden native uploader (UI wrapped and hidden with CSS)
                st.markdown('<div class="upload-files-wrapper">', unsafe_allow_html=True)
                uploader = st.file_uploader(
                    "Select PDF files",
                    type=["pdf"],
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                )
                st.markdown(
                    """
                    <style>
                    .upload-files-wrapper {
                        height: 0 !important;
                        margin: 0 !important;
                        padding: 0 !important;
                        overflow: hidden !important;
                    }
                    .st-emotion-cache-1atoy9e {
                        flex: 0 0 330px !important;
                    }
                    [data-testid="stFileUploader"] {
                        position: absolute !important;
                        width: 1px !important;
                        height: 1px !important;
                        opacity: 0 !important;
                        pointer-events: none !important;
                        overflow: hidden !important;
                        margin: 0 !important;
                        padding: 0 !important;
                    }
                    [data-testid="stFileUploadDropzone"] { display: none !important; }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

                if uploader:
                    st.session_state.uploaded_files = uploader
                    st.rerun()

                components.html(
                    """
                    <div id="custom-upload-zone" style="
                            border:1px dashed rgba(16, 78, 255, 0.18);
                            background: linear-gradient(180deg, #f3f7ff 0%, #eef6ff 100%);
                            border-radius:12px;
                            padding:28px 36px;
                            text-align:center;
                            cursor:pointer;
                            color:#0b1220;
                            min-height:200px;
                            font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    ">
                        <div style="margin-bottom:8px;"><img src="https://www.svgrepo.com/show/302427/cloud-upload.svg" width=56 height=56 style="opacity:.95;"/></div>
                        <div style="margin:8px 0 6px 0;">
                            <span style="font-weight:700; color:#ffffff; background:#0066ff; padding:10px 28px; border-radius:8px; display:inline-block; font-size:16px; letter-spacing:0.1px;">＋&nbsp;&nbsp;Select files</span>
                        </div>
                        <div style="color:#0b1220; font-size:15px; margin-top:20px; font-weight:600;">Add PDF, image, Word, Excel, and <strong>PowerPoint</strong> files</div>
                        <div style="margin-top:10px; color:#334155; font-size:13px;">
                            Supported formats:
                            <span style="background:#fde8ea; color:#b91c1c; padding:4px 8px; margin-left:8px; border-radius:12px; font-weight:700; font-size:12px;">PDF</span>
                            <span style="background:#e6f7ff; color:#0b6b9a; padding:4px 8px; margin-left:6px; border-radius:12px; font-weight:700; font-size:12px;">DOC</span>
                            <span style="background:#ecfdf5; color:#047857; padding:4px 8px; margin-left:6px; border-radius:12px; font-weight:700; font-size:12px;">XLS</span>
                            <span style="background:#fff7ed; color:#b45309; padding:4px 8px; margin-left:6px; border-radius:12px; font-weight:700; font-size:12px;">PPT</span>
                            <span style="background:#fff9db; color:#b45309; padding:4px 8px; margin-left:6px; border-radius:12px; font-weight:700; font-size:12px;">PNG</span>
                            <span style="background:#fff1d6; color:#92400e; padding:4px 8px; margin-left:6px; border-radius:12px; font-weight:700; font-size:12px;">JPG</span>
                        </div>
                    </div>
                    <script>
                        const tryBind = () => {
                            const zone = document.getElementById('custom-upload-zone');
                            const input = window.parent.document.querySelector('input[type="file"]');
                            if (zone && input) {
                                zone.addEventListener('click', () => input.click());
                                // also add keyboard accessibility
                                zone.setAttribute('tabindex', 0);
                                zone.addEventListener('keydown', (e) => {
                                    if (e.key === 'Enter' || e.key === ' ') input.click();
                                });
                            } else {
                                setTimeout(tryBind, 250);
                            }
                        };
                        tryBind();
                    </script>
                    """,
                    height=200,
            )
            else:
                # Hidden uploader for adding more files
                if 'add_more_key' not in st.session_state:
                    st.session_state.add_more_key = 0
                
                # CSS to hide the uploader but keep it functional
                st.markdown(
                    """
                    <style>
                    /* Hide the uploader wrapper/container in this section */
                    /* We target the specific uploader by ensuring this style is only injected here */
                    div[data-testid="stFileUploader"] {
                        position: fixed !important;
                        top: 0 !important;
                        left: 0 !important;
                        width: 1px !important;
                        height: 1px !important;
                        opacity: 0 !important;
                        overflow: hidden !important;
                        z-index: -1 !important;
                        pointer-events: none !important;
                    }
                    div[data-testid="stFileUploadDropzone"] {
                        opacity: 0 !important;
                        height: 1px !important;
                        width: 1px !important;
                        overflow: hidden !important;
                    }
                    </style>
                    """, 
                    unsafe_allow_html=True
                )
                
                new_files = st.file_uploader(
                    "Add more files", 
                    type=["pdf"], 
                    accept_multiple_files=True, 
                    key=f"add_more_{st.session_state.add_more_key}",
                    label_visibility="collapsed"
                )

                if new_files:
                    current.extend(new_files)
                    st.session_state.uploaded_files = current
                    # Invalidate meta to trigger regeneration
                    if 'uploaded_meta' in st.session_state:
                        del st.session_state.uploaded_meta
                    st.session_state.add_more_key += 1
                    st.rerun()

                # Ensure metadata for uploaded files (rotation, pages)
                if 'uploaded_meta' not in st.session_state or len(st.session_state.uploaded_meta) != len(current):
                    meta = []
                    for f in current:
                        fname = getattr(f, 'name', str(f))
                        pages = ''
                        thumb_b64 = None
                        # Try to detect PDF pages if PyPDF2 available
                        try:
                            from PyPDF2 import PdfReader
                            f.seek(0)
                            reader = PdfReader(f)
                            pages = len(reader.pages)
                            # Generate thumbnail preview
                            f.seek(0)
                            content = f.read()
                            f.seek(0)
                            try:
                                thumb_b64 = generate_thumbnail(pdf_bytes=content, page=0, size=(180, 240))
                            except Exception:
                                thumb_b64 = None
                            f.seek(0)
                        except Exception:
                            pages = ''
                        meta.append({'name': fname, 'rotation': 0, 'pages': pages, 'thumb': thumb_b64})
                    st.session_state.uploaded_meta = meta

                # Removed advanced toolbar and extra uploader to match pixel-spec UI

                files = st.session_state.get('uploaded_files', [])
                meta = st.session_state.get('uploaded_meta', [])

                # --- PREVIEW MODAL ---
                if st.session_state.get('preview_file_index') is not None:
                    idx = st.session_state.preview_file_index
                    if 0 <= idx < len(files):
                        with st.container():
                            col_p1, col_p2 = st.columns([0.9, 0.1])
                            with col_p1:
                                st.subheader(f"Preview: {meta[idx].get('name')}")
                            with col_p2:
                                if st.button("✖", key="close_preview"):
                                    st.session_state.preview_file_index = None
                                    st.rerun()
                            
                            # Prepare data for render_exhibit_preview
                            f = files[idx]
                            f.seek(0)
                            content = f.read()
                            f.seek(0)
                            
                            exhibit_data = {
                                'name': meta[idx].get('name'),
                                'page_count': meta[idx].get('pages'),
                                'thumbnail': meta[idx].get('thumb'),
                                'content': content,
                                'filename': meta[idx].get('name')
                            }
                            render_exhibit_preview(exhibit_data)
                            st.divider()
                
                # --- View Mode Toggle ---
                if 'view_mode' not in st.session_state:
                    st.session_state.view_mode = 'files'

                # Custom Toolbar
                st.markdown("""
                <style>
                    /* Style for the toolbar container */
                    .toolbar-container {
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        padding: 8px 0;
                        margin-bottom: 16px;
                    }
                    /* Hide default radio buttons */
                    div[data-testid="stRadio"] > div {
                        flex-direction: row;
                        gap: 0px;
                        background: #f2f5fb;
                        border: 1px solid #e4e9f2;
                        border-radius: 8px;
                        padding: 2px;
                    }
                    div[data-testid="stRadio"] label {
                        background: transparent;
                        padding: 6px 16px;
                        border-radius: 6px;
                        margin: 0;
                        border: none;
                        color: #64748B;
                        font-weight: 500;
                        cursor: pointer;
                        transition: all 0.2s;
                    }
                    div[data-testid="stRadio"] label[data-checked="true"] {
                        background: #eaf1ff;
                        color: #1064FF;
                        font-weight: 600;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                    }
                    /* Style for Add button override */
                    button[kind="secondary"] {
                        border: 1px solid #e4e9f2;
                        color: #475569;
                    }
                </style>
                """, unsafe_allow_html=True)

                col_tb_1, col_tb_2, col_tb_3, col_tb_4, col_tb_5, col_tb_6, col_tb_7 = st.columns([0.22, 0.12, 0.08, 0.08, 0.08, 0.27, 0.15])
                
                with col_tb_1:
                    # View Toggle
                    view_mode = st.radio(
                        "View Mode",
                        ["📄 Files", "▦ Pages"],
                        index=0 if st.session_state.view_mode == 'files' else 1,
                        horizontal=True,
                        label_visibility="collapsed",
                        key="view_mode_selector"
                    )
                    # Update state based on selection
                    new_mode = 'files' if "Files" in view_mode else 'pages'
                    if new_mode != st.session_state.view_mode:
                        st.session_state.view_mode = new_mode
                        st.rerun()

                with col_tb_2:
                    # Add Button - This uses JS to trigger the hidden uploader
                    components.html("""
                    <div id="btn-add-files-toolbar" style="
                        display:flex; align-items:center; gap:6px;
                        padding:6px 12px; background:#fff; border:1px solid #e4e9f2;
                        border-radius:8px; color:#475569; font-size:14px; font-family:sans-serif;
                        cursor:pointer; width: fit-content; margin-top: -2px;
                    ">
                        ＋ Add <span style="font-size:10px">▼</span>
                    </div>
                    <script>
                        const tryBindToolbar = () => {
                            const btn = document.getElementById('btn-add-files-toolbar');
                            const input = window.parent.document.querySelector('input[type="file"]');
                            if (btn && input) {
                                btn.onclick = (e) => {
                                    e.preventDefault();
                                    input.click();
                                };
                            } else {
                                setTimeout(tryBindToolbar, 250);
                            }
                        };
                        tryBindToolbar();
                    </script>
                    """, height=40)

                with col_tb_3:
                    # Sort Button (Popover)
                    with st.popover("⇅", help="Sort files"):
                        sort_order = st.radio(
                            "Sort by",
                            ["Name, A-Z", "Name, Z-A"],
                            key="sort_files_radio",
                        )
                        
                        if files and meta and len(files) == len(meta):
                            # Sort logic
                            zipped = list(zip(files, meta))
                            reverse = (sort_order == "Name, Z-A")
                            
                            # Sort by name
                            zipped.sort(key=lambda x: x[1].get('name', '').lower(), reverse=reverse)
                            
                            sorted_files, sorted_meta = zip(*zipped)
                            # Convert back to list and check if order changed to avoid unnecessary reruns
                            new_files = list(sorted_files)
                            new_meta = list(sorted_meta)
                            
                            # Only update if changed
                            current_names = [m.get('name') for m in meta]
                            new_names = [m.get('name') for m in new_meta]
                            
                            if current_names != new_names:
                                st.session_state.uploaded_files = new_files
                                st.session_state.uploaded_meta = new_meta
                                st.rerun()

                with col_tb_4:
                     if st.button("↺", help="Rotate Left", disabled=False, key="btn_rotate_left"):
                         if meta:
                             for m in meta:
                                 m['rotation'] = (m.get('rotation', 0) - 90) % 360
                             st.session_state.uploaded_meta = meta
                             st.rerun()

                with col_tb_5:
                     if st.button("↻", help="Rotate Right", disabled=False, key="btn_rotate_right"):
                         if meta:
                             for m in meta:
                                 m['rotation'] = (m.get('rotation', 0) + 90) % 360
                             st.session_state.uploaded_meta = meta
                             st.rerun()

                with col_tb_7:
                    if st.button("Done →", type="primary", use_container_width=True):
                        navigator.next_stage()
                        st.rerun()

                # --- Render Content based on View Mode ---
                
                if st.session_state.view_mode == 'files':
                    # FILES VIEW (Existing Card Grid)
                    n = len(files)
                    selected_idx = st.session_state.get('selected_upload_index', 0)
                    
                    # Determine global rotation state from first item (assuming uniform rotation)
                    first_rotation = 0
                    if meta and len(meta) > 0:
                        first_rotation = meta[0].get('rotation', 0)
                    
                    is_landscape = (first_rotation % 180 != 0)
                    
                    # Dimensions based on orientation
                    if is_landscape:
                        stack_w, stack_h, stack_mt, action_t, action_r = 202, 156, 35, -47, -8
                        card_w = 238  # 202 + 36 padding
                    else:
                        stack_w, stack_h, stack_mt, action_t, action_r = 156, 202, 12, -25, -30
                        card_w = 192



                    row_html = ['<div class="cards-row">']
                    for i in range(n):
                        m = meta[i]
                        name = m.get('name')
                        pages = f"{m.get('pages')} pages" if m.get('pages') else ''
                        
                        ext = (name.split('.')[-1].lower() if name and '.' in name else 'pdf')
                        pill_bg = '#fde8ea' if ext == 'pdf' else '#fdecc8'
                        pill_fg = '#b91c1c' if ext == 'pdf' else '#8a6a00'
                        display_name = f"{name[:22]}{'...' if len(name)>22 else ''}" if name else ''
                        thumb_b64 = m.get('thumb')
                        rotation = m.get('rotation', 0)
                        
                        # Calculate image style for rotation
                        if is_landscape:
                            # Image is portrait (156x202) but container is landscape (202x156)
                            # We need to center and rotate it
                            # Unrotated center: (78, 101). Container center: (101, 78).
                            # Left offset: 101 - 78 = 23. Top offset: 78 - 101 = -23.
                            img_style = f"width: {stack_h}px; height: {stack_w}px; transform: rotate({rotation}deg); position: absolute; left: 23px; top: -23px; transition: transform 0.3s ease;"
                        else:
                            img_style = f"width: 100%; height: 100%; transform: rotate({rotation}deg); transition: transform 0.3s ease;"

                        thumb_inner = (
                            f'<img src="data:image/jpeg;base64,{thumb_b64}" style="{img_style}" />'
                            if thumb_b64 else '<strong>EXHIBIT</strong>'
                        )
                        card = f"""
                        <div class="card">
                            <div class="stack">
                                 <div class="actions-pane">
                                    <a class="act" href="javascript:void(0)" onclick="sendAction('preview', {i})" title="Preview">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path d="M11 10h3v1h-3v3h-1v-3H7v-1h3V7h1zm4.433 4.733L20 19.3l-.7.7-4.567-4.567a6.5 6.5 0 1 1 .7-.7M10.5 16a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11"></path></svg>
                                    </a>
                                    <a class="act" href="javascript:void(0)" onclick="sendAction('rotate', {i})" title="Rotate">
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"><path fill="currentColor" fill-rule="evenodd" d="M18.238 6.982V4h.89l.005 4.46h-4.461v-.89h2.895a7.1 7.1 0 0 0-5.558-2.678c-3.932 0-7.12 3.196-7.12 7.137a7.13 7.13 0 0 0 3.171 5.94l-.494.742A8.03 8.03 0 0 1 4 12.03C4 7.595 7.586 4 12.009 4a7.99 7.99 0 0 1 6.229 2.982M9.398 18.67c.557.22 1.14.37 1.732.444l-.11.886a8.2 8.2 0 0 1-1.95-.502zm3.52.44a7.2 7.2 0 0 0 1.733-.453l.329.829a7 7 0 0 1-1.947.508zm4.595-2.554.69.565a8 8 0 0 1-1.46 1.389l-.527-.72a7 7 0 0 0 1.297-1.234m1.498-3.23.875.164c-.09.484-.386 1.51-.613 1.92l-.807-.374c.252-.546.436-1.12.545-1.71m.597-3.83a8.5 8.5 0 0 1 .392 1.98l-.887.062a7.4 7.4 0 0 0-.35-1.762z" clip-rule="evenodd"></path></svg>
                                    </a>
                                    <a class="act" href="javascript:void(0)" onclick="sendAction('duplicate', {i})" title="Duplicate">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M19.368 4H8.632A.63.63 0 0 0 8 4.632v10.736c0 .35.283.632.632.632h10.736a.63.63 0 0 0 .632-.632V4.632A.63.63 0 0 0 19.368 4M19 15H9V5h10zM5 19v-2H4v2.333c0 .368.299.667.667.667H7v-1zm3 0h4v1H8zm7-2v2h-2v1h2.333a.667.667 0 0 0 .667-.667V17zM4.667 8H7v1H5v2H4V8.667C4 8.299 4.299 8 4.667 8M5 12H4v4h1z" clip-rule="evenodd"></path></svg>
                                    </a>
                                    <a class="act" href="javascript:void(0)" onclick="sendAction('delete', {i})" title="Delete" style="color:#ef4444;">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path d="M16 4v2.999L20 7v1l-2.066-.001L17.143 20H6.857L6.066 7.999 4 8V7l4-.001V4zm1 4H7l.737 11h8.526zm-4.5 1v9h-1V9zM10 9v9H9V9zm5 0v9h-1V9zm0-4H9v2h6z"></path></svg>
                                    </a>
                                </div>
                                <div class="page back"></div>
                                <div class="page front">{thumb_inner}</div>
                            </div>
                            <div class="badge" style="background:{pill_bg};color:{pill_fg};">{display_name}</div>
                            <div class="pages">{pages}</div>
                        </div>
                        """
                        row_html.append(card)

                        # Logic moved to main script at the end
                        pass


                        if i < n - 1:
                            row_html.append('<div class="plus-dot">+</div>')
                    
                    row_html.append("""
                        <div class="add-slot" id="card-add-files">
                            <div>
                                <div class="plus-dot" style="margin: 0 auto 12px auto;">+</div>
                                Add PDF,<br/>image, Word,<br/>Excel, and<br/><strong>PowerPoint</strong><br/>files
                            </div>
                        </div>
                    """)
                    row_html.append('</div>')
                    
                    # Styles for the card component
                    styles = f"""
                    <style>
                    .cards-row {{ 
                        display:flex; 
                        gap:24px; 
                        align-items:flex-start; 
                        flex-wrap: wrap;
                        border-radius:5px; 
                        box-sizing:border-box;
                        overflow-x: auto;
                        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                        /* Minimal padding to remove empty space */
                        padding: 4px 16px 16px 16px;
                    }}
                    .card {{ 
                        width:192px; 
                        min-height: 297px;
                        border-radius:5px; 
                        padding:16px; 
                        position:relative; 
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                    }}
                    .card:hover {{
                        background:#eaf1ff;
                    }}
                    .card:hover .actions-pane {{
                        display: flex;
                    }}
                    .stack {{ 
                        position:relative; 
                        width:{stack_w}px; 
                        height:{stack_h}px; 
                        margin-bottom: 16px;
                        margin-top: {stack_mt}px;
                    }}
                    .page {{ 
                        position:absolute; 
                        top:0; left:0; 
                        width:100%; height:100%; 
                        background:#fff; 
 
                        border:1px solid #e5eaf2; 
                        border-radius:2px; 
                        box-shadow:0 2px 5px rgba(0,0,0,0.1);
                    }}
                    /* Decorative back page */
                    .page.back {{ 
                        transform:translate(-8px, -8px); 
                        opacity:1;
                        z-index: 1;
                    }}
                    
                    .page.front {{ 
                        display:flex; 
                        align-items:center; 
                        justify-content:center; 
                        overflow:hidden; 
                        z-index: 2;
                    }}
                    .page.front img {{ width:100%; height:100%; object-fit:contain; }}
                    
                    .actions-pane {{ 
                        position:absolute; 
                        top:{action_t}px; 
                        right:{action_r}px; 
                        background:#fff; 
                        border:1px solid #e4e9f2; 
                        border-radius:6px; 
                        padding:2px; 
                        display:none; 
                        gap:2px; 
                        box-shadow:0 2px 8px rgba(0,0,0,0.08);
                        z-index: 10;
                    }}
                    
                    .act {{ 
                        width:30px; 
                        height:30px; 
                        display:flex; 
                        align-items:center; 
                        justify-content:center; 
                        font-size:14px; 
                        color:#334155; 
                        border-radius:4px; 
                        cursor: pointer;
                        text-decoration: none;
                    }}
                    .act:hover {{ background: #f1f5f9; }}
                    
                    .badge {{ 
                        display:inline-block; 
                        padding:4px 12px; 
                        border-radius:12px; 
                        font-weight:600; 
                        font-size:12px; 
                        max-width:180px; 
                        overflow:hidden; 
                        text-overflow:ellipsis; 
                        white-space:nowrap; 
                        margin-bottom: 4px;
                        position: absolute;
                        bottom: 55px;
                    }}
                    .pages {{ 
                        font-size:14px; 
                        color:#a3a3a3; 
                        text-align:center; 
                        font-weight:500;
                        position: absolute;
                        bottom: 35px;
                    }}
                    .plus-dot {{ width:34px; height:34px; border-radius:50%; background:#cfe3ff; color:#fff; display:flex; align-items:center; justify-content:center; font-size:20px; align-self:center; }}
                    .add-slot {{ 
                        width:210px; 
                        height:300px; 
                        border-radius:12px; 
                        border:2px dotted #3B82F6; 
                        background:#eef6ff; 
                        display:flex; 
                        align-items:center; 
                        justify-content:center; 
                        color:#3B82F6; 
                        font-weight:600; 
                        text-align:center; 
                        padding: 16px;
                    }}
                    </style>
                    """
                    
                    script = """
                    <script>
                        // Add file click handler
                        const card = document.getElementById('card-add-files');
                        const input = window.parent.document.querySelector('input[type="file"]');
                        if (card && input) {
                            card.addEventListener('click', () => {
                                input.click();
                            });
                            card.style.cursor = 'pointer';
                        }

                        // Bridge function to communicate with Streamlit
                        // Define it on window to ensure global access
                        window.sendAction = function(action, id) {
                            try {
                                const value = action + ":" + id;
                                console.log("Sending action:", value);
                                
                                // Try multiple selectors to find the input
                                let bridgeInput = window.parent.document.querySelector('input[placeholder="bridge_connector_v2"]');
                                if (!bridgeInput) {
                                    // Fallback: Try finding by aria-label
                                    bridgeInput = window.parent.document.querySelector('input[aria-label="internal_action_bridge"]');
                                }
                                
                                if (!bridgeInput) {
                                    const allInputs = window.parent.document.querySelectorAll('input[type="text"]');
                                    for (let inp of allInputs) {
                                        if (inp.getAttribute('aria-label') === 'internal_action_bridge') {
                                            bridgeInput = inp;
                                            break;
                                        }
                                    }
                                }

                                if (bridgeInput) {
                                    // Set value using native setter to bypass React/Streamlit overrides
                                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                    nativeInputValueSetter.call(bridgeInput, value);
                                    
                                    // Dispatch input event to trigger Streamlit update
                                    bridgeInput.dispatchEvent(new Event('input', { bubbles: true }));
                                    
                                    // FORCE COMMIT: Simulate Enter key and Blur to ensure Streamlit picks up the change
                                    bridgeInput.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 13 }));
                                    bridgeInput.dispatchEvent(new Event('change', { bubbles: true }));
                                    bridgeInput.dispatchEvent(new Event('blur', { bubbles: true }));
                                    
                                    // Visual feedback in the card itself
                                    const btn = event.currentTarget;
                                    if(btn) {
                                        btn.innerHTML = '...';
                                        btn.style.pointerEvents = 'none';
                                    }
                                } else {
                                    console.error("Bridge input not found!");
                                    alert("Connection Error: internal_action_bridge input missing. Please contact support.");
                                }
                            } catch (e) {
                                console.error("Bridge Error:", e);
                                alert("Error executing action: " + e.message);
                            }
                        }
                    </script>
                    """
                    components.html(styles + "\n".join(row_html) + script, height=320)
                
                else:
                    # PAGES VIEW (New Implementation)
                    # We need to render every page of every PDF
                    # This could be resource intensive, so we limit or paginate if necessary, but request says "display all pages"
                    
                    # 1. Collect all pages
                    all_pages = []
                    for i, f in enumerate(files):
                        m = meta[i]
                        num_pages = int(m.get('pages', 0)) if m.get('pages') else 0
                        
                        # Cache key for this file
                        # Use name + size to be more unique than just name
                        file_id = f"{f.name}_{f.size}"
                        
                        # We need to read the file content to generate thumbnails
                        f.seek(0)
                        bytes_content = f.read()
                        
                        for p_idx in range(num_pages):
                            # Check if we have this thumb in session state cache? 
                            # For now, generate on fly or use a simple cache key
                            cache_key = f"thumb_{file_id}_{p_idx}"
                            if cache_key not in st.session_state:
                                try:
                                    t = generate_thumbnail(pdf_bytes=bytes_content, page=p_idx, size=(150, 200))
                                    st.session_state[cache_key] = t
                                except:
                                    st.session_state[cache_key] = None
                            
                            thumb = st.session_state[cache_key]
                            all_pages.append({
                                'file_index': i,
                                'file_name': m.get('name'),
                                'page_index': p_idx,
                                'thumb': thumb,
                                'total_pages': num_pages
                            })
                    
                    # 2. Render Grid of Pages
                    # Similar CSS but simpler cards
                    
                    page_html = ['<div class="pages-grid">']
                    for item in all_pages:
                        thumb_b64 = item['thumb']
                        thumb_img = (
                            f'<img src="data:image/jpeg;base64,{thumb_b64}" />'
                            if thumb_b64 else '<div class="no-thumb">Page ' + str(item['page_index']+1) + '</div>'
                        )
                        
                        card = f"""
                        <div class="page-card">
                            <div class="page-preview">
                                {thumb_img}
                                <div class="page-number">{item['page_index'] + 1}</div>
                            </div>
                            <div class="file-label">{item['file_name']}</div>
                        </div>
                        """
                        # Add plus dot between pages? The screenshot shows plus dots between files, 
                        # but typically page view is just a grid. 
                        # The third screenshot shows + buttons between pages.
                        page_html.append(card)
                        page_html.append('<div class="plus-dot-small">+</div>')

                    # Remove last plus dot
                    if page_html and page_html[-1] == '<div class="plus-dot-small">+</div>':
                        page_html.pop()
                        
                    page_html.append('</div>')
                    
                    styles = """
                    <style>
                    .pages-grid {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 16px;
                        align-items: center;
                        padding: 16px;
                        font-family: Inter, sans-serif;
                    }
                    .page-card {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        width: 160px;
                    }
                    .page-preview {
                        width: 140px;
                        height: 190px;
                        background: #fff;
                        border: 1px solid #e5eaf2;
                        border-radius: 4px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        position: relative;
                        overflow: hidden;
                        margin-bottom: 8px;
                    }
                    .page-preview img {
                        width: 100%;
                        height: 100%;
                        object-fit: contain;
                    }
                    .page-number {
                        position: absolute;
                        bottom: 4px;
                        right: 4px;
                        background: rgba(0,0,0,0.5);
                        color: #fff;
                        font-size: 10px;
                        padding: 2px 6px;
                        border-radius: 4px;
                    }
                    .file-label {
                        font-size: 11px;
                        color: #64748B;
                        text-align: center;
                        max-width: 100%;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }
                    .plus-dot-small {
                        width: 24px; 
                        height: 24px; 
                        border-radius: 50%; 
                        background: #cfe3ff; 
                        color: #fff; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        font-size: 16px;
                    }
                    </style>
                    """
                    
                    components.html(styles + "\n".join(page_html), height=600, scrolling=True)


            #     st.markdown("""
            #     <script>
            #         const bindUpload = () => {{
            #             const slot = document.getElementById('upload-slot');
            #             const input = window.parent.document.querySelector('input[type="file"]');
            #             if (slot && input) {{
            #                 slot.addEventListener('click', () => input.click());
            #                 slot.style.cursor = 'pointer';
            #             }} else {{
            #                 setTimeout(bindUpload, 250);
            #             }}
            #         }};
            #         bindUpload();
            #     </script>
            # """, height=600)

                if st.session_state.get('insert_position') is not None:
                    pos = st.session_state.insert_position
                    st.markdown(f"**Insert files at position {pos + 1}**")
                    new_files = st.file_uploader("Select files to insert", accept_multiple_files=True, key="insert_files")
                    if new_files:
                        uploaded = st.session_state.get('uploaded_files', [])
                        meta = st.session_state.get('uploaded_meta', [])
                        insert_at = pos
                        for af in new_files:
                            uploaded.insert(insert_at, af)
                            pages = ''
                            thumb_b64 = None
                            try:
                                from PyPDF2 import PdfReader
                                af.seek(0)
                                reader = PdfReader(af)
                                pages = len(reader.pages)
                                # Generate thumbnail
                                af.seek(0)
                                content = af.read()
                                af.seek(0)
                                try:
                                    thumb_b64 = generate_thumbnail(pdf_bytes=content, page=0, size=(180, 240))
                                except Exception:
                                    thumb_b64 = None
                                af.seek(0)
                            except Exception:
                                pages = ''
                            meta.insert(insert_at, {'name': getattr(af, 'name', str(af)), 'rotation': 0, 'pages': pages, 'thumb': thumb_b64})
                            insert_at += 1
                        st.session_state.uploaded_files = uploaded
                        st.session_state.uploaded_meta = meta
                        st.session_state.pop('insert_position', None)
                        st.experimental_rerun()

        elif upload_method == "ZIP Archive":
            zip_file = st.file_uploader("Select ZIP file", type=["zip"])
            if zip_file:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    zip_path = os.path.join(tmp_dir, "upload.zip")
                    with open(zip_path, 'wb') as f:
                        f.write(zip_file.read())
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        for member in zip_ref.namelist():
                            if ".." in member or member.startswith("/"):
                                continue  # Skip dangerous paths
                            zip_ref.extract(member, tmp_dir)
                        pdf_files = list(Path(tmp_dir).rglob("*.pdf"))
                        st.info(f"Found {len(pdf_files)} PDF files in ZIP")
                        st.session_state.zip_files = [str(p) for p in pdf_files]

    with tab2:
        url_list = render_url_manager()

    with tab3:
        st.subheader("Google Drive Integration")
        st.info("💡 Connect to Google Drive to process folders directly")

        drive_url = st.text_input(
            "Google Drive Folder URL",
            placeholder="https://drive.google.com/drive/folders/..."
        )

        if drive_url:
            st.warning("🚧 Google Drive OAuth integration - coming in next update")

    st.markdown('</div>', unsafe_allow_html=True)

    # Check if we have files to proceed
    has_files = (
        len(st.session_state.get('uploaded_files', [])) > 0 or
        len(st.session_state.get('zip_files', [])) > 0 or
        len(get_url_list()) > 0
    )

    # Navigation buttons removed as per user request (replaced by "Done" button in toolbar)
    # navigator.render_navigation_buttons(
    #    next_label="Move to Classification",
    #    next_disabled=not has_files
    # )


def render_stage_3_classify(navigator: StageNavigator, config: Dict):
    """Stage 3: AI Classification"""

    st.markdown('<div class="stage-container">', unsafe_allow_html=True)

    render_context_summary()

    # Get files to classify
    files = st.session_state.get('uploaded_files', [])
    zip_files = st.session_state.get('zip_files', [])

    if not files and not zip_files:
        st.warning("No files to classify. Go back to upload stage.")
        navigator.render_navigation_buttons()
        return

    # Check if already classified
    classifications = get_classifications()

    if not classifications:
        # Run classification
        st.subheader("🤖 Classifying Documents...")

        api_key = st.session_state.get('anthropic_api_key')
        classifier = AIClassifier(api_key=api_key)

        all_classifications = []
        total_files = len(files) + len(zip_files)

        progress_bar = st.progress(0)
        status_text = st.empty()

        # Process uploaded files
        for i, file in enumerate(files):
            status_text.text(f"Classifying: {file.name}")

            # Read file content
            content = file.read()
            file.seek(0)  # Reset for later use

            result = classifier.classify_document(
                pdf_content=content,
                filename=file.name,
                visa_type=config['visa_type'],
                document_id=f"file_{i}"
            )
            all_classifications.append(result)
            progress_bar.progress((i + 1) / total_files)

        # Process zip files
        for i, file_path in enumerate(zip_files):
            filename = os.path.basename(file_path)
            status_text.text(f"Classifying: {filename}")

            with open(file_path, 'rb') as f:
                content = f.read()

            result = classifier.classify_document(
                pdf_content=content,
                filename=filename,
                visa_type=config['visa_type'],
                document_id=f"zip_{i}"
            )
            all_classifications.append(result)
            progress_bar.progress((len(files) + i + 1) / total_files)

        status_text.text("✓ Classification complete!")
        save_classifications(all_classifications)
        classifications = all_classifications

    # Show classification UI
    updated = render_classification_ui(classifications, config['visa_type'])
    save_classifications(updated)

    st.markdown('</div>', unsafe_allow_html=True)

    navigator.render_navigation_buttons(
        next_label="Review Classification"
    )

def render_stage_4_review(navigator: StageNavigator, config: Dict):
    """Stage 4: Manual Review & Reorder"""

    st.markdown('<div class="stage-container">', unsafe_allow_html=True)

    render_context_summary()

    # Convert classifications to exhibits if not done
    classifications = get_classifications()
    exhibits = get_exhibits()

    if classifications and not exhibits:
        set_exhibits_from_classifications(classifications, config['numbering_style'])

    # Render editor
    updated_exhibits = render_exhibit_editor(config['numbering_style'])

    st.markdown('</div>', unsafe_allow_html=True)

    navigator.render_navigation_buttons(
        next_label="Generate Exhibits",
        next_disabled=len(updated_exhibits) == 0
    )


def render_stage_5_generate(navigator: StageNavigator, config: Dict):
    """Stage 5: Background Processing"""
    st.markdown('<div class="stage-container">', unsafe_allow_html=True)

    render_context_summary()

    processor = get_processor()

    # If a previous run failed, surface the error and allow retry
    if processor.has_error:
        render_processing_ui()
        state = processor.state
        st.error(f"Generation failed: {state.error_message or 'Unknown error occurred during exhibit generation.'}")

        if st.button("Retry Generate Exhibit Package", type="primary", use_container_width=True):
            generate_exhibits_v2(config)
    
    elif not processor.is_running and not processor.is_complete:
        # Initial state: ready to start processing
        st.info("Click below to generate your exhibit package")

        if st.button("🚀 Generate Exhibit Package", type="primary", use_container_width=True):
            # Start background processing and immediately rerun so the
            # next render enters the `processor.is_running` branch and
            # shows the progress UI.
            generate_exhibits_v2(config)
            st.rerun()

    elif processor.is_running:
        # Show progress
        result = render_processing_ui()
        if result:
            st.session_state.processing_complete = True
            navigator.next_stage()
            st.rerun()

    elif processor.is_complete:
        # Transfer results from background processor to session state
        if hasattr(processor.state, 'result') and processor.state.result:
            result = processor.state.result
            st.session_state.output_file = result.get('output_file')
            st.session_state.exhibit_list = result.get('exhibit_list', [])
            st.session_state.cover_letter_path = result.get('cover_letter_path')
            st.session_state.filing_instructions_path = result.get('filing_instructions_path')
            
            # Transfer compression stats if available
            if 'compressed_size' in result and 'original_size' in result:
                st.session_state.compression_stats = {
                    'original_size': result['original_size'],
                    'compressed_size': result['compressed_size'],
                    'avg_reduction': result.get('avg_reduction', 0),
                    'method': result.get('compression_method', 'unknown'),
                    'quality': config.get('quality_preset', 'medium')
                }
        
        st.success("✓ Generation complete!")
        navigator.next_stage()
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Don't show nav buttons while processing
    if not processor.is_running:
        navigator.render_navigation_buttons()
    st.write("Processor status:", processor.state.status)
    st.write("Processor error:", processor.state.error_message)
    

def render_stage_6_complete(navigator: StageNavigator, config: Dict):
    """Stage 6: Download & Share"""
    st.markdown('<div class="stage-container">', unsafe_allow_html=True)

    st.markdown('<div class="success-box">✓ Your exhibit package is ready!</div>', unsafe_allow_html=True)

    # Statistics
    if st.session_state.get('exhibit_list'):
        st.subheader("📊 Statistics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Exhibits", len(st.session_state.exhibit_list))

        with col2:
            total_pages = sum(ex.get('pages', 0) for ex in st.session_state.exhibit_list)
            st.metric("Total Pages", total_pages)

        with col3:
            if st.session_state.compression_stats:
                reduction = st.session_state.compression_stats.get('avg_reduction', 0)
                st.metric("Size Reduction", f"{reduction:.1f}%")
            else:
                st.metric("Size Reduction", "-")

        with col4:
            if st.session_state.compression_stats:
                size_mb = st.session_state.compression_stats.get('compressed_size', 0) / (1024*1024)
                st.metric("Final Size", f"{size_mb:.1f} MB")
            else:
                st.metric("Final Size", "-")

    st.divider()
    # Download section
    col1, col2 = st.columns(2)
    outlits = st.session_state.get('output_file')

    with col1:
        st.subheader("📥 Download")
        if st.session_state.get('output_file') and os.path.exists(st.session_state.output_file):
            # Read exhibit package bytes to ensure reliable download
            with open(st.session_state.output_file, 'rb') as f:
                package_bytes = f.read()
            case_context = get_case_context()
            beneficiary = case_context.beneficiary_name or "Package"
            st.download_button(
                label="📥 Download Exhibit Package",
                data=package_bytes,
                file_name=f"Exhibit_Package_{beneficiary}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

            # Shareable link
            st.divider()
            render_link_generator(st.session_state.output_file)

            # Cover letter download (if generated)
            cover_path = st.session_state.get('cover_letter_path')
            if cover_path and os.path.exists(cover_path):
                with open(cover_path, 'rb') as cf:
                    cover_bytes = cf.read()
                st.download_button(
                    label="📄 Download Cover Letter",
                    data=cover_bytes,
                    file_name=f"Cover_Letter_{beneficiary}_{datetime.now().strftime('%Y%m%d')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="secondary",
                    use_container_width=True
                )

            # Filing instructions (DIY) download
            filing_path = st.session_state.get('filing_instructions_path') or result.get('filing_instructions_path') if 'result' in locals() else None
            if not filing_path:
                # also check session state directly
                filing_path = st.session_state.get('filing_instructions_path')

            if filing_path and os.path.exists(filing_path):
                with open(filing_path, 'rb') as ff:
                    filing_bytes = ff.read()
                st.download_button(
                    label="🧾 Download Filing Instructions (DIY)",
                    data=filing_bytes,
                    file_name=f"Filing_Instructions_{beneficiary}_{datetime.now().strftime('%Y%m%d')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="secondary",
                    use_container_width=True
                )

            # Comparable Evidence (CE) letter UI
            with st.expander("🧾 Comparable Evidence Letter (O-1A/O-1B/EB-1A)", expanded=False):
                st.caption("Generate an explanation letter when a standard criterion does not readily apply.")
                ce_criterion = st.text_input("Criterion letter (A, B, C, ...)", max_chars=1, key="ce_criterion")
                ce_reason = st.text_area("Why the standard criterion does not apply", key="ce_reason")
                ce_evidence = st.text_area("Describe the comparable evidence being submitted", key="ce_evidence")

                # Show previously generated CE letters
                ce_paths = st.session_state.get('ce_letter_paths', {}) or {}
                if ce_paths:
                    for k, p in ce_paths.items():
                        if os.path.exists(p):
                            with open(p, 'rb') as _f:
                                _b = _f.read()
                            st.download_button(
                                label=f"📄 Download CE Letter ({k})",
                                data=_b,
                                file_name=os.path.basename(p),
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True
                            )

                if st.button("Generate CE Letter", type="secondary", use_container_width=True, key="gen_ce"):
                    if not ce_criterion:
                        st.error("Please enter a criterion letter (e.g., A).")
                    elif not ce_reason or not ce_evidence:
                        st.error("Please provide both a reason and the comparable evidence description.")
                    else:
                        try:
                            from templates.docx_engine import generate_ce_letter

                            case_context = get_case_context()
                            case_data = {
                                'beneficiary_name': getattr(case_context, 'beneficiary_name', None) or 'Beneficiary',
                                'petitioner_name': getattr(case_context, 'petitioner_name', None) or 'Petitioner',
                                'visa_type': config.get('visa_type') or getattr(case_context, 'visa_category', None) or 'O-1A',
                                'service_center': getattr(case_context, 'service_center', None) or 'California Service Center',
                            }

                            crit = ce_criterion.strip().upper()
                            tmp_ce = os.path.join(tempfile.gettempdir(), f"CE_Letter_{beneficiary}_{crit}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx")
                            generate_ce_letter(case_data, crit, ce_reason, ce_evidence, tmp_ce)

                            # Save path in session state keyed by criterion
                            ce_paths = st.session_state.get('ce_letter_paths', {}) or {}
                            ce_paths[crit] = tmp_ce
                            st.session_state.ce_letter_paths = ce_paths

                            # Read bytes and show immediate download
                            with open(tmp_ce, 'rb') as _f:
                                ce_bytes = _f.read()

                            st.success(f"CE letter for Criterion {crit} generated.")
                            st.download_button(
                                label=f"📄 Download CE Letter ({crit})",
                                data=ce_bytes,
                                file_name=os.path.basename(tmp_ce),
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True,
                            )

                        except Exception as e:
                            st.error(f"Error generating CE letter: {e}")
                            import traceback
                            traceback.print_exc()

            # Legal brief: if already generated, show download; otherwise offer Generate button
            brief_path = st.session_state.get('legal_brief_path')
            if brief_path and os.path.exists(brief_path):
                with open(brief_path, 'rb') as bf:
                    brief_bytes = bf.read()
                st.download_button(
                    label="📘 Download Legal Brief",
                    data=brief_bytes,
                    file_name=f"Legal_Brief_{beneficiary}_{datetime.now().strftime('%Y%m%d')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="secondary",
                    use_container_width=True
                )
            else:
                if st.button("🖋️ Generate Legal Brief", type="secondary", use_container_width=True):
                    try:
                        from templates.docx_engine import generate_legal_brief

                        case_context = get_case_context()
                        case_data = {
                            'beneficiary_name': getattr(case_context, 'beneficiary_name', None) or 'Beneficiary',
                            'petitioner_name': getattr(case_context, 'petitioner_name', None) or 'Petitioner',
                            'visa_type': config.get('visa_type') or getattr(case_context, 'visa_category', None) or 'O-1A',
                            'nationality': getattr(case_context, 'nationality', None) or '',
                            'field': getattr(case_context, 'field', None) or '',
                            'job_title': getattr(case_context, 'job_title', None) or '',
                            'duration': getattr(case_context, 'duration', None) or '3 years',
                            'processing_type': getattr(case_context, 'processing_type', None) or 'Regular',
                            'filing_fee': getattr(case_context, 'filing_fee', None) or '$460',
                            'premium_fee': getattr(case_context, 'premium_fee', None) or '$2,805',
                            'criteria_met': getattr(case_context, 'criteria_met', []) or []
                        }

                        exhibits = st.session_state.get('exhibit_list', [])

                        analyses = st.session_state.get('criterion_analyses') or {}
                        if not analyses:
                            claimed = case_data.get('criteria_met') or []
                            if not claimed:
                                claimed = ['A', 'C', 'F']
                            for i, letter in enumerate(claimed):
                                ex = None
                                if i < len(exhibits):
                                    ex = exhibits[i].get('title') or exhibits[i].get('name') or exhibits[i].get('filename')
                                ex_ref = f"See Exhibit {ex}" if ex else "See attached exhibits"
                                analyses[letter] = f"Analysis for criterion {letter}. {ex_ref}. (Auto-generated placeholder.)"

                        tmp_path = os.path.join(tempfile.gettempdir(), f"Legal_Brief_{beneficiary}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx")
                        generate_legal_brief(case_data, exhibits, analyses, tmp_path)

                        with open(tmp_path, 'rb') as bf:
                            brief_bytes = bf.read()

                        st.session_state.legal_brief_path = tmp_path
                        st.success("Legal brief generated — the download will begin below.")
                        st.download_button(
                            label="📘 Download Legal Brief",
                            data=brief_bytes,
                            file_name=f"Legal_Brief_{beneficiary}_{datetime.now().strftime('%Y%m%d')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary",
                            use_container_width=True,
                        )

                    except Exception as e:
                        st.error(f"Error generating legal brief: {e}")
                        import traceback
                        traceback.print_exc()

        else:
            st.warning("Output file not found. Try regenerating.")

    with col2:
        st.subheader("📧 Share")

        case_context = get_case_context()
        case_info = {
            'beneficiary_name': case_context.beneficiary_name or 'N/A',
            'petitioner_name': case_context.petitioner_name or 'N/A',
            'visa_type': config['visa_type'],
            'processing_type': case_context.processing_type or 'Regular',
            'exhibit_count': len(st.session_state.get('exhibit_list', [])),
            'page_count': sum(ex.get('pages', 0) for ex in st.session_state.get('exhibit_list', []))
        }

        render_email_form(
            case_info=case_info,
            file_path=st.session_state.get('output_file'),
            download_link=None  # Would be shareable link URL
        )

    st.markdown('</div>', unsafe_allow_html=True)

    navigator.render_navigation_buttons()


def generate_exhibits_v2(config: Dict):
    """Generate exhibits with V2 processing"""
    processor = get_processor()
    processor.reset()

    # Get files
    files = st.session_state.get('uploaded_files', [])
    zip_files = st.session_state.get('zip_files', [])
    exhibits = get_exhibits()

    def process_func(proc: BackgroundProcessor) -> Dict[str, Any]:
        """Background processing function"""
        import time

        result = {
            'exhibits': [],
            'total_pages': 0,
            'original_size': 0,
            'compressed_size': 0,
            'output_file': None
        }

        # Create temp directory
        tmp_dir = tempfile.mkdtemp()

        try:
            # Step 1: Extract/Save files
            proc.update_step("extract", "running")
            file_paths = []

            for i, file in enumerate(files):
                file_path = os.path.join(tmp_dir, file.name)
                with open(file_path, 'wb') as f:
                    f.write(file.read())
                file_paths.append(file_path)
                proc.set_step_progress("extract", (i + 1) / max(len(files), 1) * 100)

            for file_path in zip_files:
                if not isinstance(file_path, str) or not os.path.isabs(file_path):
                    proc.update_step("extract", "error", error_message=f"Invalid zip file path: {file_path}")
                    continue
                if os.path.exists(file_path):
                    dest = os.path.join(tmp_dir, os.path.basename(file_path))
                    shutil.copy(file_path, dest)
                    file_paths.append(dest)
                else:
                    proc.update_step("extract", "error", error_message=f"Zip file not found: {file_path}")

            proc.complete_step("extract")

            # Step 2: Compress
            pdf_handler = PDFHandler(
                enable_compression=config['enable_compression'],
                quality_preset=config['quality_preset'],
                smallpdf_api_key=config['smallpdf_api_key']
            )

            compression_results = []
            if config['enable_compression'] and pdf_handler.compressor:
                proc.update_step("compress", "running")

                for i, file_path in enumerate(file_paths):
                    comp_result = pdf_handler.compressor.compress(file_path)
                    if comp_result.get('success'):
                        compression_results.append(comp_result)
                        result['original_size'] += comp_result.get('original_size', 0)
                        result['compressed_size'] += comp_result.get('compressed_size', 0)
                    proc.set_step_progress("compress", (i + 1) / len(file_paths) * 100)

            proc.complete_step("compress")

            # Step 3: Number exhibits
            proc.update_step("number", "running")
            numbered_files = []
            exhibit_list = []
            # Initialize AI classifier for labels/analysis (uses Anthropic or OpenAI if available)
            api_key = st.session_state.get('anthropic_api_key')
            classifier = AIClassifier(api_key=api_key)

            for i, file_path in enumerate(file_paths):
                # Get exhibit number
                if config['numbering_style'] == "letters":
                    exhibit_num = chr(65 + i) if i < 26 else f"A{chr(65 + i - 26)}"
                elif config['numbering_style'] == "numbers":
                    exhibit_num = str(i + 1)
                else:
                    exhibit_num = to_roman(i + 1)

                # Track info (initial)
                exhibit_info = {
                    'number': exhibit_num,
                    'title': Path(file_path).stem,
                    'filename': os.path.basename(file_path),
                    'pages': get_pdf_page_count(file_path)
                }

                # Attempt AI-driven short label and content analysis BEFORE creating cover
                short_label = None
                analysis = None
                try:
                    with open(file_path, 'rb') as _f:
                        content_bytes = _f.read()
                    print(f'AI analyzing file: {os.path.basename(file_path)}')
                    print(f'Visa type: {config.get("visa_type")}')
                    short_label = classifier.generate_short_label(content_bytes, exhibit_info['filename'], config['visa_type'])
                    analysis = classifier.analyze_pdf(content_bytes, exhibit_info['filename'], config['visa_type'])
                    if short_label:
                        exhibit_info['title'] = short_label
                    if analysis:
                        exhibit_info['analysis'] = analysis
                        # copy common fields for easy access
                        exhibit_info['summary'] = analysis.get('summary')
                        exhibit_info['document_type'] = analysis.get('document_type')
                        exhibit_info['dates'] = analysis.get('dates')
                        exhibit_info['forms'] = analysis.get('forms')
                        exhibit_info['visa_mentions'] = analysis.get('visa_mentions')
                        exhibit_info['entities'] = analysis.get('entities')
                except Exception as e:
                    print(f"AI analysis error for {file_path}: {e}")

                # Add exhibit number with cover page, including title/summary when available
                try:
                    # Provide extracted text and bytes so the PDF handler can append full text and images
                    # Only extract and attach full text/images if user enabled the option
                    if config.get('include_full_text_images'):
                        try:
                            extracted_text = classifier.extract_text_from_pdf(content_bytes, max_chars=200000)
                        except Exception:
                            extracted_text = None
                    else:
                        extracted_text = None

                    numbered_file = pdf_handler.add_exhibit_number_with_cover(
                        file_path,
                        exhibit_num,
                        title=exhibit_info.get('title'),
                        summary=exhibit_info.get('summary'),
                        extracted_text=extracted_text,
                        content_bytes=content_bytes if config.get('include_full_text_images') else None
                    )
                except Exception as e:
                    print(f"Error creating numbered file for {file_path}: {e}")
                    numbered_file = pdf_handler.add_exhibit_number_with_cover(file_path, exhibit_num)

                numbered_files.append(numbered_file)

                if i < len(compression_results):
                    exhibit_info['compression'] = {
                        'reduction': compression_results[i].get('reduction_percent', 0),
                        'method': compression_results[i].get('method', 'none')
                    }

                exhibit_list.append(exhibit_info)
                result['total_pages'] += exhibit_info['pages']

                proc.set_step_progress("number", (i + 1) / len(file_paths) * 100)

            proc.complete_step("number")

            # Step 4: Generate TOC
            if config['add_toc']:
                proc.update_step("toc", "running")
                toc_file = pdf_handler.generate_table_of_contents(
                    exhibit_list,
                    config['visa_type'],
                    os.path.join(tmp_dir, "TOC.pdf")
                )
                numbered_files.insert(0, toc_file)
            proc.complete_step("toc")

            # Step 5: Generate Cover Letter
            if config['add_cover_letter']:
                proc.update_step("cover", "running")
                try:
                    # Get case context
                    case_context = get_case_context()
                    
                    # Debug: Print case context
                    print(f"Case context: {case_context}")
                    
                    # Create template engine
                    engine = DOCXTemplateEngine()
                    
                    # Prepare case data
                    case_data = {
                        'visa_type': config['visa_type'],
                        'beneficiary_name': getattr(case_context, 'beneficiary_name', None) or 'Beneficiary',
                        'petitioner_name': getattr(case_context, 'petitioner_name', None) or 'Petitioner',
                        'service_center': getattr(case_context, 'service_center', None) or 'California Service Center',
                        'nationality': getattr(case_context, 'nationality', None) or '',
                        'job_title': getattr(case_context, 'job_title', None) or '',
                        'field': getattr(case_context, 'field', None) or '',
                        'duration': getattr(case_context, 'duration', None) or '3 years',
                        'processing_type': getattr(case_context, 'processing_type', None) or 'Regular',
                        'filing_fee': getattr(case_context, 'filing_fee', None) or '$460',
                        'premium_fee': getattr(case_context, 'premium_fee', None) or '$2,805'
                    }
                    
                    # Debug: Print case data
                    print(f"Case data: {case_data}")
                    
                    # Generate cover letter
                    cover_letter_path = os.path.join(tmp_dir, "Cover_Letter.docx")
                    from templates.docx_engine import CaseData
                    case_obj = CaseData(**case_data)
                    engine.generate_cover_letter(case_obj, exhibit_list, cover_letter_path)
                    result['cover_letter_path'] = cover_letter_path
                    
                    print(f"Cover letter generated: {cover_letter_path}")
                    
                except Exception as e:
                    print(f"Error generating cover letter: {e}")
                    import traceback
                    traceback.print_exc()
                    result['cover_letter_path'] = None
            proc.complete_step("cover")

            # Step 5a: Generate Filing Instructions (DIY) if requested
            proc.update_step("filing_instructions", "running")
            if config.get('add_filing_instructions'):
                try:
                    # Create template engine
                    engine = DOCXTemplateEngine()

                    # Reuse case context
                    case_context = get_case_context()
                    case_data = {
                        'visa_type': config['visa_type'],
                        'beneficiary_name': getattr(case_context, 'beneficiary_name', None) or 'Beneficiary',
                        'petitioner_name': getattr(case_context, 'petitioner_name', None) or 'Petitioner',
                        'service_center': getattr(case_context, 'service_center', None) or 'California Service Center',
                        'nationality': getattr(case_context, 'nationality', None) or '',
                        'job_title': getattr(case_context, 'job_title', None) or '',
                        'field': getattr(case_context, 'field', None) or '',
                        'duration': getattr(case_context, 'duration', None) or '3 years',
                        'processing_type': getattr(case_context, 'processing_type', None) or 'Regular',
                        'filing_fee': getattr(case_context, 'filing_fee', None) or '$460',
                        'premium_fee': getattr(case_context, 'premium_fee', None) or '$2,805',
                        'criteria_met': getattr(case_context, 'criteria_met', []) or []
                    }

                    from templates.docx_engine import CaseData
                    case_obj = CaseData(**case_data)
                    filing_path = os.path.join(tmp_dir, "Filing_Instructions.docx")
                    engine.generate_filing_instructions(case_obj, exhibit_list, filing_path)
                    result['filing_instructions_path'] = filing_path

                except Exception as e:
                    print(f"Error generating filing instructions: {e}")
                    import traceback
                    traceback.print_exc()
                    result['filing_instructions_path'] = None
            proc.complete_step("filing_instructions")

            # Step 5: Merge / select output file
            proc.update_step("merge", "running")

            if numbered_files:
                if config['merge_pdfs']:
                    # Standard behavior: merge all numbered PDFs into one package
                    output_file = os.path.join(tmp_dir, "final_package.pdf")
                    merged_file = pdf_handler.merge_pdfs(numbered_files, output_file)

                    # Copy to persistent location
                    final_output = os.path.join(
                        tempfile.gettempdir(),
                        f"exhibit_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    )
                    shutil.copy(merged_file, final_output)
                    result['output_file'] = final_output
                else:
                    # If user chose not to merge, still provide a single downloadable file
                    # by exposing the first numbered exhibit as the package output.
                    first_file = numbered_files[0]
                    final_output = os.path.join(
                        tempfile.gettempdir(),
                        f"exhibit_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    )
                    shutil.copy(first_file, final_output)
                    result['output_file'] = final_output
            else:
                # No numbered files were produced; leave output_file as None
                result['output_file'] = None

            proc.complete_step("merge")

            # Step 6: Finalize
            proc.update_step("finalize", "running")

            # Save results to session state
            st.session_state.exhibit_list = exhibit_list
            
            if compression_results:
                avg_reduction = (
                    (1 - result['compressed_size'] / max(result['original_size'], 1)) * 100
                    if result['original_size'] > 0 else 0
                )
                st.session_state.compression_stats = {
                    'original_size': result['original_size'],
                    'compressed_size': result['compressed_size'],
                    'avg_reduction': avg_reduction,
                    'method': compression_results[0].get('method', 'unknown'),
                    'quality': config['quality_preset']
                }

            st.session_state.exhibits_generated = True
            proc.complete_step("finalize")
            return result

        except Exception as e:
            raise RuntimeError(f"Failed to process exhibits: {e}") from e

    processor.start_processing(process_func)


def get_pdf_page_count(pdf_path: str) -> int:
    """Get number of pages in PDF"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except:
        return 0


def to_roman(num: int) -> str:
    """Convert number to Roman numeral"""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syms[i]
            num -= val[i]
        i += 1
    return roman_num


def main():
    """Main application entry point"""
    init_session_state()

    # Hidden input for JS-to-Python communication
    # We use on_change to ensure the command is processed before the rest of the script
    st.text_input(
        "internal_action_bridge", 
        key="action_command", 
        label_visibility="collapsed",
        on_change=process_bridge_command,
        placeholder="bridge_connector_v2"
    )
    st.markdown(
        """
        <style>
        /* Robust hiding that keeps element interactive */
        div[data-testid="stTextInput"]:has(input[placeholder="bridge_connector_v2"]) {
            opacity: 0;
            height: 1px;
            overflow: hidden;
            position: absolute;
            z-index: -1;
        }
        /* Fallback */
        input[placeholder="bridge_connector_v2"] {
            opacity: 0;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )

    # Header
    st.markdown('<div class="main-header">📄 Visa Exhibit Generator <span class="version-badge">V2.0</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Professional exhibit packages with AI-powered classification</div>', unsafe_allow_html=True)

    # Sidebar config
    config = render_sidebar()

    # Stage Navigator
    navigator = StageNavigator()

    # Render stage header
    render_stage_header(navigator)

    # Render current stage
    current_stage = navigator.current_stage

    if current_stage == 0:
        render_stage_1_context(navigator)
    elif current_stage == 1:
        render_stage_2_upload(navigator, config)
    elif current_stage == 2:
        render_stage_3_classify(navigator, config)
    elif current_stage == 3:
        render_stage_4_review(navigator, config)
    elif current_stage == 4:
        render_stage_5_generate(navigator, config)
    elif current_stage == 5:
        render_stage_6_complete(navigator, config)


if __name__ == "__main__":
    main()
