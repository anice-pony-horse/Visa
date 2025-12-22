"""
Thumbnail Grid Component - SmallPDF-Style UI
=============================================

Implements Issue #7: 60-Thumbnail Grid Preview

Features:
- Large thumbnail view (150x200px per card)
- 6-column grid (shows ~60 items at once)
- Hover actions (view, rotate, duplicate, delete)
- Drag handles for reordering
- Insert buttons between cards
"""

import streamlit as st
import base64
from io import BytesIO
from typing import List, Dict, Any, Optional
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for PDF thumbnail generation
try:
    from pdf2image import convert_from_path, convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available - thumbnails will use placeholders")

try:
    import fitz  # PyMuPDF - faster alternative
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def generate_thumbnail(
    pdf_path: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    page: int = 0,
    size: tuple = (150, 200),
    rotation: int = 0
) -> Optional[str]:
    """
    Generate base64 thumbnail for first page of PDF.

    Args:
        pdf_path: Path to PDF file
        pdf_bytes: PDF content as bytes
        page: Page number (0-indexed)
        size: Thumbnail size (width, height)
        rotation: Rotation angle (0, 90, 180, 270)

    Returns:
        Base64 encoded JPEG string or None
    """
    if not pdf_path and not pdf_bytes:
        return None

    # Try PyMuPDF first (faster)
    if PYMUPDF_AVAILABLE:
        try:
            if pdf_path:
                doc = fitz.open(pdf_path)
            else:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            if len(doc) == 0:
                return None

            page_obj = doc[min(page, len(doc) - 1)]
            
            # Apply rotation if needed
            if rotation != 0:
                page_obj.set_rotation(rotation)

            # Render to image
            mat = fitz.Matrix(size[0] / page_obj.rect.width, size[1] / page_obj.rect.height)
            pix = page_obj.get_pixmap(matrix=mat)

            # Convert to base64
            img_bytes = pix.tobytes("jpeg")
            doc.close()

            return base64.b64encode(img_bytes).decode()

        except Exception as e:
            logger.warning(f"PyMuPDF thumbnail failed: {e}")

    # Try pdf2image
    if PDF2IMAGE_AVAILABLE:
        try:
            if pdf_path:
                images = convert_from_path(
                    pdf_path,
                    first_page=page + 1,
                    last_page=page + 1,
                    size=size
                )
            else:
                images = convert_from_bytes(
                    pdf_bytes,
                    first_page=page + 1,
                    last_page=page + 1,
                    size=size
                )

            if images:
                buffered = BytesIO()
                images[0].save(buffered, format="JPEG", quality=70)
                return base64.b64encode(buffered.getvalue()).decode()

        except Exception as e:
            logger.warning(f"pdf2image thumbnail failed: {e}")

    return None


def get_placeholder_thumbnail() -> str:
    """Generate a placeholder thumbnail for PDFs that can't be rendered."""
    # Simple gray rectangle with PDF icon
    svg = '''
    <svg xmlns="http://www.w3.org/2000/svg" width="150" height="200" viewBox="0 0 150 200">
        <rect width="150" height="200" fill="#f0f0f0"/>
        <rect x="40" y="50" width="70" height="90" fill="#ffffff" stroke="#cccccc" stroke-width="2"/>
        <text x="75" y="100" font-family="Arial" font-size="12" fill="#999999" text-anchor="middle">PDF</text>
        <path d="M85 50 L85 70 L105 70 L85 50 Z" fill="#cccccc"/>
    </svg>
    '''
    return base64.b64encode(svg.encode()).decode()


# CSS for SmallPDF-style grid
GRID_CSS = """
<style>
.exhibit-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 16px;
    padding: 20px;
    background: #fafafa;
    border-radius: 8px;
    min-height: 400px;
}

.exhibit-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 8px;
    cursor: grab;
    transition: all 0.2s ease;
    position: relative;
}

.exhibit-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    transform: translateY(-2px);
    border-color: #3b82f6;
}

.exhibit-card.selected {
    border-color: #3b82f6;
    border-width: 2px;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.exhibit-card:active {
    cursor: grabbing;
}

.exhibit-thumbnail {
    width: 100%;
    height: 180px;
    object-fit: contain;
    background: #f5f5f5;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.exhibit-thumbnail img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

.exhibit-number {
    position: absolute;
    top: 4px;
    left: 4px;
    background: #3b82f6;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: bold;
}

.exhibit-criterion {
    position: absolute;
    top: 4px;
    right: 4px;
    background: #10b981;
    color: white;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
}

.exhibit-name {
    font-size: 12px;
    font-weight: 500;
    margin-top: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #333;
}

.exhibit-pages {
    font-size: 11px;
    color: #666;
    margin-top: 2px;
}

.exhibit-actions {
    position: absolute;
    top: 8px;
    right: 8px;
    display: none;
    gap: 4px;
    background: rgba(255,255,255,0.9);
    padding: 4px;
    border-radius: 4px;
}

.exhibit-card:hover .exhibit-actions {
    display: flex;
}

.action-btn {
    width: 24px;
    height: 24px;
    border-radius: 4px;
    border: none;
    cursor: pointer;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
}

.action-btn:hover {
    background: #e0e0e0;
}

.action-btn.delete:hover {
    background: #fee2e2;
    color: #dc2626;
}

.insert-zone {
    position: absolute;
    right: -12px;
    top: 50%;
    transform: translateY(-50%);
    width: 24px;
    height: 24px;
    background: #10b981;
    color: white;
    border-radius: 50%;
    display: none;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    cursor: pointer;
    z-index: 10;
}

.exhibit-card:hover .insert-zone {
    display: flex;
}

.drag-handle {
    position: absolute;
    bottom: 4px;
    left: 50%;
    transform: translateX(-50%);
    width: 40px;
    height: 4px;
    background: #e0e0e0;
    border-radius: 2px;
    cursor: grab;
}

.exhibit-card:hover .drag-handle {
    background: #3b82f6;
}

/* Responsive grid */
@media (max-width: 1200px) {
    .exhibit-grid {
        grid-template-columns: repeat(4, 1fr);
    }
}

@media (max-width: 900px) {
    .exhibit-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}

@media (max-width: 600px) {
    .exhibit-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
</style>
"""


def render_thumbnail_grid(
    exhibits: List[Dict[str, Any]],
    columns: int = 6,
    show_actions: bool = True,
    on_delete: Optional[callable] = None,
    on_select: Optional[callable] = None
) -> List[Dict[str, Any]]:
    """
    Render SmallPDF-style thumbnail grid.

    Args:
        exhibits: List of exhibit dicts with path, name, page_count, thumbnail
        columns: Number of columns (default 6 for ~60 items visible)
        show_actions: Whether to show hover action buttons
        on_delete: Callback for delete action
        on_select: Callback for selection

    Returns:
        Updated exhibits list (with any changes)
    """
    # Inject CSS
    st.markdown(GRID_CSS, unsafe_allow_html=True)

    # Generate thumbnails if not present
    for exhibit in exhibits:
        if "thumbnail" not in exhibit or not exhibit["thumbnail"]:
            exhibit["thumbnail"] = generate_thumbnail(
                pdf_path=exhibit.get("path"),
                pdf_bytes=exhibit.get("content")
            ) or get_placeholder_thumbnail()

    # Render grid using Streamlit columns
    cols = st.columns(columns)

    for i, exhibit in enumerate(exhibits):
        with cols[i % columns]:
            # Card container
            thumbnail = exhibit.get("thumbnail", get_placeholder_thumbnail())
            is_svg = thumbnail.startswith("PHN2")  # SVG starts with <svg in base64

            # Determine image format
            if is_svg:
                img_src = f"data:image/svg+xml;base64,{thumbnail}"
            else:
                img_src = f"data:image/jpeg;base64,{thumbnail}"

            # Build card HTML
            exhibit_num = exhibit.get("exhibit_number", exhibit.get("number", chr(65 + i)))
            criterion = exhibit.get("criterion_letter", "")
            name = exhibit.get("name", exhibit.get("filename", f"Document {i + 1}"))
            pages = exhibit.get("page_count", exhibit.get("pages", "?"))

            card_html = f"""
            <div class="exhibit-card" data-index="{i}">
                <span class="exhibit-number">Exhibit {exhibit_num}</span>
                {"<span class='exhibit-criterion'>Crit. " + criterion + "</span>" if criterion else ""}
                <div class="exhibit-thumbnail">
                    <img src="{img_src}" alt="{name}" />
                </div>
                <div class="exhibit-name" title="{name}">
                    {name[:25]}{"..." if len(name) > 25 else ""}
                </div>
                <div class="exhibit-pages">{pages} pages</div>
                <div class="drag-handle"></div>
            </div>
            """

            st.markdown(card_html, unsafe_allow_html=True)

            # Action buttons (using Streamlit buttons for interactivity)
            if show_actions:
                action_cols = st.columns(4)

                with action_cols[0]:
                    if st.button("👁️", key=f"view_{i}", help="View"):
                        st.session_state[f"preview_{i}"] = True

                with action_cols[1]:
                    if st.button("↕️", key=f"move_{i}", help="Move"):
                        st.session_state[f"move_mode_{i}"] = True

                with action_cols[2]:
                    if st.button("📋", key=f"dup_{i}", help="Duplicate"):
                        exhibits.insert(i + 1, exhibit.copy())
                        st.rerun()

                with action_cols[3]:
                    if st.button("🗑️", key=f"del_{i}", help="Delete"):
                        if on_delete:
                            on_delete(i)
                        else:
                            exhibits.pop(i)
                            st.rerun()

    return exhibits


def render_exhibit_preview(exhibit: Dict[str, Any]):
    """Render full preview modal for an exhibit."""
    st.markdown("### Preview")
    st.markdown(f"**{exhibit.get('name', 'Document')}**")

    if exhibit.get("path") and os.path.exists(exhibit["path"]):
        with open(exhibit["path"], "rb") as f:
            pdf_bytes = f.read()
            st.download_button(
                "Download PDF",
                pdf_bytes,
                file_name=exhibit.get("filename", "document.pdf"),
                mime="application/pdf"
            )

    # Show thumbnail larger
    thumbnail = exhibit.get("thumbnail")
    if thumbnail:
        if thumbnail.startswith("PHN2"):
            st.markdown(f'<img src="data:image/svg+xml;base64,{thumbnail}" width="300">', unsafe_allow_html=True)
        else:
            st.markdown(f'<img src="data:image/jpeg;base64,{thumbnail}" width="300">', unsafe_allow_html=True)

    # Exhibit info
    st.markdown(f"""
    - **Pages:** {exhibit.get('page_count', '?')}
    - **Category:** {exhibit.get('category', 'Unknown')}
    - **Criterion:** {exhibit.get('criterion_letter', 'N/A')}
    """)


def render_compact_list(
    exhibits: List[Dict[str, Any]],
    show_numbers: bool = True
) -> List[Dict[str, Any]]:
    """
    Render a compact list view (alternative to grid).

    Args:
        exhibits: List of exhibit dicts
        show_numbers: Whether to show exhibit numbers

    Returns:
        Updated exhibits list
    """
    for i, exhibit in enumerate(exhibits):
        cols = st.columns([1, 6, 2, 1])

        with cols[0]:
            if show_numbers:
                num = exhibit.get("exhibit_number", chr(65 + i))
                st.markdown(f"**{num}**")

        with cols[1]:
            name = exhibit.get("name", exhibit.get("filename", f"Document {i + 1}"))
            st.text(name[:50])

        with cols[2]:
            criterion = exhibit.get("criterion_letter", "")
            if criterion:
                st.markdown(f"`{criterion}`")

        with cols[3]:
            if st.button("🗑️", key=f"list_del_{i}"):
                exhibits.pop(i)
                st.rerun()

    return exhibits
