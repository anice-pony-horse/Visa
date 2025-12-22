"""
Exhibit Editor Component (Feature 5)
=====================================

Manual exhibit reorder with AI text instructions.
- Drag-and-drop exhibit list
- Inline rename
- AI instruction text box
- Quick sort actions
"""

import streamlit as st
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
import re


@dataclass
class ExhibitItem:
    """Represents an exhibit in the editor"""
    id: str
    number: str  # A, B, C or 1, 2, 3 or I, II, III
    name: str
    filename: str
    category: str
    confidence: float
    pages: int = 0
    file_path: Optional[str] = None
    order: int = 0
    rotation: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'number': self.number,
            'name': self.name,
            'filename': self.filename,
            'category': self.category,
            'confidence': self.confidence,
            'pages': self.pages,
            'file_path': self.file_path,
            'order': self.order
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExhibitItem':
        return cls(**data)


class ExhibitEditor:
    """Editor for reordering and renaming exhibits"""

    def __init__(self):
        """Initialize exhibit editor"""
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state"""
        if 'exhibits' not in st.session_state:
            st.session_state.exhibits = []
        if 'exhibit_order_history' not in st.session_state:
            st.session_state.exhibit_order_history = []

    @property
    def exhibits(self) -> List[ExhibitItem]:
        """Get current exhibit list"""
        return [
            ExhibitItem.from_dict(e) if isinstance(e, dict) else e
            for e in st.session_state.exhibits
        ]

    def set_exhibits(self, exhibits: List[ExhibitItem]):
        """Set the exhibit list"""
        st.session_state.exhibits = [e.to_dict() for e in exhibits]
        self._save_history()

    def _save_history(self):
        """Save current order to history"""
        current = [e['id'] for e in st.session_state.exhibits]
        st.session_state.exhibit_order_history.append(current)
        # Keep last 10 states
        if len(st.session_state.exhibit_order_history) > 10:
            st.session_state.exhibit_order_history.pop(0)

    def undo(self):
        """Undo last reorder"""
        if len(st.session_state.exhibit_order_history) > 1:
            st.session_state.exhibit_order_history.pop()  # Remove current
            previous = st.session_state.exhibit_order_history[-1]
            self.reorder(previous)

    def reorder(self, new_order: List[str]):
        """Reorder exhibits based on list of IDs"""
        id_to_exhibit = {
            (e.get('id') if isinstance(e, dict) else e.id): e
            for e in st.session_state.exhibits
        }
        st.session_state.exhibits = [
            id_to_exhibit[eid] for eid in new_order
            if eid in id_to_exhibit
        ]
        self._renumber()

    def _renumber(self, style: str = 'letters'):
        """Renumber exhibits based on current order"""
        for i, e in enumerate(st.session_state.exhibits):
            if style == 'letters':
                number = chr(65 + i) if i < 26 else f"A{chr(65 + i - 26)}"
            elif style == 'numbers':
                number = str(i + 1)
            else:  # roman
                number = self._to_roman(i + 1)

            if isinstance(e, dict):
                e['number'] = number
                e['order'] = i
            else:
                e.number = number
                e.order = i
                st.session_state.exhibits[i] = e.to_dict()

    def _to_roman(self, num: int) -> str:
        """Convert number to Roman numeral"""
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
        roman = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman += syms[i]
                num -= val[i]
            i += 1
        return roman

    def rename(self, exhibit_id: str, new_name: str):
        """Rename an exhibit"""
        for e in st.session_state.exhibits:
            eid = e.get('id') if isinstance(e, dict) else e.id
            if eid == exhibit_id:
                if isinstance(e, dict):
                    e['name'] = new_name
                else:
                    e.name = new_name
                break

    def move(self, exhibit_id: str, direction: int):
        """Move exhibit up (-1) or down (+1)"""
        exhibits = st.session_state.exhibits
        ids = [e.get('id') if isinstance(e, dict) else e.id for e in exhibits]

        if exhibit_id not in ids:
            return

        idx = ids.index(exhibit_id)
        new_idx = idx + direction

        if 0 <= new_idx < len(ids):
            ids[idx], ids[new_idx] = ids[new_idx], ids[idx]
            self.reorder(ids)

    def sort_by_category(self):
        """Sort exhibits by category"""
        exhibits = self.exhibits
        sorted_exhibits = sorted(exhibits, key=lambda e: (e.category, -e.confidence))
        self.set_exhibits(sorted_exhibits)

    def sort_by_confidence(self):
        """Sort exhibits by confidence score (highest first)"""
        exhibits = self.exhibits
        sorted_exhibits = sorted(exhibits, key=lambda e: -e.confidence)
        self.set_exhibits(sorted_exhibits)

    def sort_alphabetical(self):
        """Sort exhibits alphabetically by name"""
        exhibits = self.exhibits
        sorted_exhibits = sorted(exhibits, key=lambda e: e.name.lower())
        self.set_exhibits(sorted_exhibits)

    def apply_ai_instruction(self, instruction: str) -> bool:
        """
        Apply AI instruction to reorder exhibits.
        Returns True if successful.
        """
        instruction_lower = instruction.lower()
        exhibits = self.exhibits

        # Pattern: "move X before Y" or "put X after Y"
        move_pattern = r"(?:move|put)\s+(?:exhibit\s+)?(\w+)\s+(before|after)\s+(?:exhibit\s+)?(\w+)"
        match = re.search(move_pattern, instruction_lower)
        if match:
            source, position, target = match.groups()
            return self._move_relative(source.upper(), target.upper(), position == 'before')

        # Pattern: "group all X together" or "put all X at the beginning/end"
        group_pattern = r"(?:group|put)\s+all\s+(\w+)\s+(?:together|at the (beginning|end))"
        match = re.search(group_pattern, instruction_lower)
        if match:
            category = match.group(1)
            position = match.group(2)  # 'beginning', 'end', or None
            return self._group_category(category, position)

        # Pattern: "sort by X"
        sort_pattern = r"sort\s+by\s+(category|confidence|name|alphabetical)"
        match = re.search(sort_pattern, instruction_lower)
        if match:
            sort_type = match.group(1)
            if sort_type == 'category':
                self.sort_by_category()
            elif sort_type == 'confidence':
                self.sort_by_confidence()
            elif sort_type in ['name', 'alphabetical']:
                self.sort_alphabetical()
            return True

        # Pattern: "awards first" or "letters at the end"
        position_pattern = r"(\w+)\s+(first|at the beginning|at the end|last)"
        match = re.search(position_pattern, instruction_lower)
        if match:
            category = match.group(1)
            position = 'beginning' if match.group(2) in ['first', 'at the beginning'] else 'end'
            return self._group_category(category, position)

        return False

    def _move_relative(self, source: str, target: str, before: bool) -> bool:
        """Move source exhibit before/after target"""
        exhibits = self.exhibits
        ids = [e.id for e in exhibits]

        source_idx = next((i for i, e in enumerate(exhibits) if e.number == source), None)
        target_idx = next((i for i, e in enumerate(exhibits) if e.number == target), None)

        if source_idx is None or target_idx is None:
            return False

        # Remove source
        source_id = ids.pop(source_idx)

        # Adjust target index if source was before target
        if source_idx < target_idx:
            target_idx -= 1

        # Insert at new position
        insert_idx = target_idx if before else target_idx + 1
        ids.insert(insert_idx, source_id)

        self.reorder(ids)
        return True

    def _group_category(self, category: str, position: Optional[str]) -> bool:
        """Group exhibits by category"""
        exhibits = self.exhibits
        category_lower = category.lower()

        # Find matching exhibits
        matching = [e for e in exhibits if category_lower in e.category.lower()]
        non_matching = [e for e in exhibits if category_lower not in e.category.lower()]

        if not matching:
            return False

        if position == 'beginning':
            new_order = matching + non_matching
        elif position == 'end':
            new_order = non_matching + matching
        else:
            # Just group together, keep relative position
            # Find first matching and insert all there
            first_idx = next(i for i, e in enumerate(exhibits) if category_lower in e.category.lower())
            new_order = exhibits[:first_idx] + matching + [e for e in exhibits[first_idx:] if e not in matching]

        self.set_exhibits(new_order)
        return True


def render_exhibit_editor(numbering_style: str = 'letters') -> List[ExhibitItem]:
    """
    Render the exhibit editor interface.

    Args:
        numbering_style: 'letters', 'numbers', or 'roman'

    Returns:
        List of ExhibitItem objects in final order
    """
    editor = ExhibitEditor()

    st.subheader("✏️ Review & Reorder Exhibits")

    # Quick actions and editor when in list view

    if not editor.exhibits:
        st.info("No exhibits to edit. Complete the classification stage first.")
        return []

    # Quick action buttons
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("📊 Sort by Category"):
            editor.sort_by_category()
            st.rerun()

    with col2:
        if st.button("🎯 Sort by Confidence"):
            editor.sort_by_confidence()
            st.rerun()

    with col3:
        if st.button("🔤 Sort Alphabetical"):
            editor.sort_alphabetical()
            st.rerun()

    with col4:
        if st.button("↩️ Undo"):
            editor.undo()
            st.rerun()

    with col5:
        if st.button("🔄 Reset Order"):
            # Reset to original classification order
            if 'original_exhibit_order' in st.session_state:
                editor.reorder(st.session_state.original_exhibit_order)
                st.rerun()

    st.markdown("---")

    # AI Instruction Box
    st.markdown("**🤖 AI Reorder Instructions**")
    instruction = st.text_input(
        "Describe how to reorganize exhibits",
        placeholder="E.g., 'Move all awards to the beginning', 'Put Exhibit F before Exhibit C', 'Group letters together'",
        key="ai_instruction"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Apply AI Suggestions", type="primary"):
            if instruction:
                success = editor.apply_ai_instruction(instruction)
                if success:
                    st.success("Exhibits reordered!")
                    st.rerun()
                else:
                    st.warning("Could not understand instruction. Try: 'move A before C' or 'sort by category'")

    st.markdown("---")

    # Exhibit list
    st.markdown("**📋 Exhibit Order** (drag to reorder)")

    for i, exhibit in enumerate(editor.exhibits):
        col1, col2, col3, col4, col5 = st.columns([0.5, 2.5, 1.5, 1, 0.5])

        with col1:
            # Exhibit number badge
            st.markdown(f"<div style='background:#1f77b4; color:white; padding:0.5rem; border-radius:0.25rem; text-align:center; font-weight:bold;'>{exhibit.number}</div>", unsafe_allow_html=True)

        with col2:
            # Editable name
            new_name = st.text_input(
                "Name",
                value=exhibit.name,
                key=f"name_{exhibit.id}",
                label_visibility="collapsed"
            )
            if new_name != exhibit.name:
                editor.rename(exhibit.id, new_name)

            st.caption(f"📄 {exhibit.filename} | {exhibit.pages} pages")

        with col3:
            # Category badge
            st.markdown(f"<span style='background:#e0e0e0; padding:0.25rem 0.5rem; border-radius:0.25rem;'>{exhibit.category}</span>", unsafe_allow_html=True)
            st.caption(f"Confidence: {exhibit.confidence:.0%}")

        with col4:
            # Reorder buttons
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if i > 0:
                    if st.button("↑", key=f"up_{exhibit.id}"):
                        editor.move(exhibit.id, -1)
                        st.rerun()
            with btn_col2:
                if i < len(editor.exhibits) - 1:
                    if st.button("↓", key=f"down_{exhibit.id}"):
                        editor.move(exhibit.id, 1)
                        st.rerun()

        with col5:
            pass  # Placeholder for future actions

        st.markdown("---")

    # Summary
    st.info(f"📊 {len(editor.exhibits)} exhibits | Order will be applied when generating")

    return editor.exhibits


def get_exhibits() -> List[ExhibitItem]:
    """Get exhibits from session state"""
    editor = ExhibitEditor()
    return editor.exhibits


def set_exhibits_from_classifications(classifications: List[Any], numbering_style: str = 'letters'):
    """Convert classifications to exhibits"""
    exhibits = []
    for i, c in enumerate(classifications):
        if numbering_style == 'letters':
            number = chr(65 + i) if i < 26 else f"A{chr(65 + i - 26)}"
        elif numbering_style == 'numbers':
            number = str(i + 1)
        else:
            number = _to_roman(i + 1)

        # Support both dict-based and object-based classification results safely
        if isinstance(c, dict):
            name = c.get('criterion_name', 'Unknown')
            filename = c.get('filename', '')
            category = c.get('criterion_name', 'Other')
            confidence = c.get('confidence_score', 0.5)
            file_path = c.get('file_path')
        else:
            name = getattr(c, 'criterion_name', 'Unknown')
            filename = getattr(c, 'filename', '')
            category = getattr(c, 'criterion_name', 'Other')
            confidence = getattr(c, 'confidence_score', 0.5)
            file_path = getattr(c, 'file_path', None)

        exhibit = ExhibitItem(
            id=f"exhibit_{i}",
            number=number,
            name=name,
            filename=filename,
            category=category,
            confidence=confidence,
            pages=0,
            file_path=file_path,
            order=i
        )
        exhibits.append(exhibit)

    # Save original order
    st.session_state.original_exhibit_order = [e.id for e in exhibits]

    editor = ExhibitEditor()
    editor.set_exhibits(exhibits)


def _to_roman(num: int) -> str:
    """Convert number to Roman numeral"""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    roman = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman += syms[i]
            num -= val[i]
        i += 1
    return roman
