"""
Drag-and-Drop Grid Component
=============================

Implements Issue #8: Visual Drag-and-Drop Reordering

Uses streamlit-sortables for native drag-drop functionality.
Provides multiple view modes:
- Grid view (SmallPDF style)
- List view (compact)
- Sectioned view (grouped by criterion)
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for streamlit-sortables
try:
    from streamlit_sortables import sort_items
    SORTABLES_AVAILABLE = True
except ImportError:
    SORTABLES_AVAILABLE = False
    logger.warning("streamlit-sortables not installed. Install with: pip install streamlit-sortables")


def render_sortable_grid(
    exhibits: List[Dict[str, Any]],
    multi_containers: bool = False,
    direction: str = "horizontal"
) -> List[Dict[str, Any]]:
    """
    Render drag-and-drop sortable exhibit grid.

    Args:
        exhibits: List of exhibit dicts
        multi_containers: Enable grouping by sections
        direction: 'horizontal' or 'vertical'

    Returns:
        Reordered exhibits list
    """
    if not SORTABLES_AVAILABLE:
        st.warning("Drag-and-drop requires streamlit-sortables. Install with: pip install streamlit-sortables")
        return exhibits

    if not exhibits:
        st.info("No exhibits to display")
        return exhibits

    # Prepare items for sortables
    items = []
    for i, ex in enumerate(exhibits):
        items.append({
            "id": str(i),
            "name": ex.get("name", ex.get("filename", f"Document {i + 1}"))[:30],
            "criterion": ex.get("criterion_letter", ""),
            "pages": ex.get("page_count", "?")
        })

    # Custom HTML template for items
    def item_template(item):
        criterion_badge = f'<span style="background:#10b981;color:white;padding:2px 6px;border-radius:4px;font-size:10px;margin-left:8px;">{item["criterion"]}</span>' if item["criterion"] else ""
        return f'''
        <div style="background:white;padding:12px;border-radius:8px;border:1px solid #e0e0e0;margin:4px;cursor:grab;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-weight:500;">{item["name"]}</span>
            <span>
                {criterion_badge}
                <span style="color:#666;font-size:11px;margin-left:8px;">{item["pages"]} pg</span>
            </span>
        </div>
        '''

    # Render sortable list
    try:
        sorted_items = sort_items(
            items,
            multi_containers=multi_containers,
            direction=direction
        )

        # Map back to original exhibits
        new_order = []
        for item in sorted_items:
            original_idx = int(item["id"])
            if original_idx < len(exhibits):
                new_order.append(exhibits[original_idx])

        return new_order

    except Exception as e:
        logger.error(f"Sortable render failed: {e}")
        return exhibits


def render_sectioned_sortable(
    exhibits: List[Dict[str, Any]],
    sections: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Render drag-and-drop with multiple sections.

    Args:
        exhibits: List of exhibit dicts
        sections: List of section names

    Returns:
        Dict mapping section names to exhibit lists
    """
    if not SORTABLES_AVAILABLE:
        st.warning("Drag-and-drop requires streamlit-sortables")
        return {"All": exhibits}

    # Group exhibits by section
    section_map = {section: [] for section in sections}
    section_map["Unassigned"] = []

    for exhibit in exhibits:
        category = exhibit.get("category", "")
        placed = False

        for section in sections:
            if section.lower() in category.lower() or category.lower() in section.lower():
                section_map[section].append(exhibit)
                placed = True
                break

        if not placed:
            section_map["Unassigned"].append(exhibit)

    # Prepare multi-container items
    containers = {}
    for section, items in section_map.items():
        if items:  # Only show non-empty sections
            containers[section] = [
                {
                    "id": f"{section}_{i}",
                    "name": item.get("name", "")[:25],
                    "original_idx": exhibits.index(item) if item in exhibits else i
                }
                for i, item in enumerate(items)
            ]

    try:
        # Render with multi-containers
        sorted_containers = sort_items(
            containers,
            multi_containers=True,
            direction="vertical"
        )

        # Rebuild section map with new order
        result = {}
        for section, items in sorted_containers.items():
            result[section] = []
            for item in items:
                orig_idx = item.get("original_idx", 0)
                if orig_idx < len(exhibits):
                    result[section].append(exhibits[orig_idx])

        return result

    except Exception as e:
        logger.error(f"Sectioned sortable failed: {e}")
        return section_map


def render_drag_drop_list(
    exhibits: List[Dict[str, Any]],
    numbering_style: str = "letters"
) -> List[Dict[str, Any]]:
    """
    Render a simple drag-and-drop list (fallback when sortables unavailable).

    Uses up/down buttons instead of true drag-drop.

    Args:
        exhibits: List of exhibits
        numbering_style: How to number exhibits

    Returns:
        Reordered exhibits
    """
    st.markdown("### Exhibit Order")
    st.caption("Use arrows to reorder exhibits")

    for i, exhibit in enumerate(exhibits):
        cols = st.columns([1, 1, 6, 2, 1, 1])

        # Up button
        with cols[0]:
            if i > 0:
                if st.button("⬆️", key=f"up_{i}", help="Move up"):
                    exhibits[i], exhibits[i - 1] = exhibits[i - 1], exhibits[i]
                    st.rerun()
            else:
                st.write("")

        # Down button
        with cols[1]:
            if i < len(exhibits) - 1:
                if st.button("⬇️", key=f"down_{i}", help="Move down"):
                    exhibits[i], exhibits[i + 1] = exhibits[i + 1], exhibits[i]
                    st.rerun()
            else:
                st.write("")

        # Exhibit number
        if numbering_style == "letters":
            num = chr(65 + i) if i < 26 else f"A{chr(65 + i - 26)}"
        elif numbering_style == "numbers":
            num = str(i + 1)
        else:
            num = _to_roman(i + 1)

        # Name
        with cols[2]:
            name = exhibit.get("name", exhibit.get("filename", f"Document {i + 1}"))
            st.markdown(f"**Exhibit {num}:** {name[:40]}")

        # Criterion
        with cols[3]:
            criterion = exhibit.get("criterion_letter", "")
            if criterion:
                st.markdown(f"Criterion {criterion}")

        # Delete
        with cols[4]:
            if st.button("🗑️", key=f"del_{i}"):
                exhibits.pop(i)
                st.rerun()

        # Update exhibit number
        exhibit["exhibit_number"] = num
        exhibit["number"] = num

    return exhibits


def _to_roman(num: int) -> str:
    """Convert number to Roman numeral."""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    roman = ''
    for i, v in enumerate(val):
        while num >= v:
            roman += syms[i]
            num -= v
    return roman


def render_quick_reorder_bar(exhibits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Render quick reorder toolbar with common actions.

    Args:
        exhibits: List of exhibits

    Returns:
        Potentially reordered exhibits
    """
    st.markdown("### Quick Actions")

    cols = st.columns(5)

    with cols[0]:
        if st.button("🔀 Shuffle", help="Randomize order"):
            import random
            random.shuffle(exhibits)
            st.rerun()

    with cols[1]:
        if st.button("📝 A-Z", help="Sort by name"):
            exhibits.sort(key=lambda x: x.get("name", "").lower())
            st.rerun()

    with cols[2]:
        if st.button("📊 By Criterion", help="Group by criterion"):
            exhibits.sort(key=lambda x: x.get("criterion_letter", "ZZZ"))
            st.rerun()

    with cols[3]:
        if st.button("📄 By Pages", help="Sort by page count"):
            exhibits.sort(key=lambda x: x.get("page_count", 0), reverse=True)
            st.rerun()

    with cols[4]:
        if st.button("↩️ Reset", help="Reset to original order"):
            if "original_exhibit_order" in st.session_state:
                exhibits = st.session_state.original_exhibit_order.copy()
                st.rerun()

    return exhibits


def render_move_modal(
    exhibits: List[Dict[str, Any]],
    selected_index: int
) -> Optional[int]:
    """
    Render a modal for moving an exhibit to a specific position.

    Args:
        exhibits: List of exhibits
        selected_index: Index of exhibit being moved

    Returns:
        New index if moved, None otherwise
    """
    exhibit = exhibits[selected_index]

    st.markdown(f"### Move: {exhibit.get('name', 'Document')}")

    # Position selector
    new_position = st.number_input(
        "Move to position",
        min_value=1,
        max_value=len(exhibits),
        value=selected_index + 1
    )

    cols = st.columns(2)

    with cols[0]:
        if st.button("Move", type="primary"):
            return new_position - 1

    with cols[1]:
        if st.button("Cancel"):
            return None

    return None


def get_drag_drop_state() -> Dict[str, Any]:
    """Get current drag-drop state from session."""
    return {
        "exhibits": st.session_state.get("exhibit_order", []),
        "selected": st.session_state.get("selected_exhibit", None),
        "view_mode": st.session_state.get("view_mode", "grid")
    }


def set_drag_drop_state(
    exhibits: Optional[List[Dict]] = None,
    selected: Optional[int] = None,
    view_mode: Optional[str] = None
):
    """Update drag-drop state in session."""
    if exhibits is not None:
        st.session_state["exhibit_order"] = exhibits
    if selected is not None:
        st.session_state["selected_exhibit"] = selected
    if view_mode is not None:
        st.session_state["view_mode"] = view_mode
