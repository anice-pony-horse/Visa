"""
Arrangement Chat Component - AI-Powered Exhibit Organization
=============================================================

Implements Issue #9: ChatBot for Arrangement

Features:
- Natural language arrangement instructions
- Claude-powered instruction parsing
- Smart command understanding
- Chat history with context

Example commands:
- "Put passport first"
- "Group all award documents together"
- "Sort by page count"
- "Move I-129 before I-907"
- "Put media articles after expert letters"
"""

import streamlit as st
from typing import List, Dict, Any, Optional
import json
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for Claude API
try:
    from anthropic import Anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False


class ArrangementChat:
    """
    AI-powered chat interface for exhibit arrangement.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize chat with optional API key.

        Args:
            api_key: Anthropic API key (uses env var if not provided)
        """
        import os
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None

        if self.api_key and CLAUDE_AVAILABLE:
            self.client = Anthropic(api_key=self.api_key)

    def parse_instruction(
        self,
        instruction: str,
        exhibits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Parse natural language instruction into exhibit reordering.

        Args:
            instruction: User's natural language instruction
            exhibits: Current exhibit list

        Returns:
            Dict with action and new_order
        """
        # Try AI parsing first
        if self.client:
            try:
                return self._parse_with_claude(instruction, exhibits)
            except Exception as e:
                logger.warning(f"Claude parsing failed: {e}")

        # Fall back to rule-based parsing
        return self._parse_with_rules(instruction, exhibits)

    def _parse_with_claude(
        self,
        instruction: str,
        exhibits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use Claude to parse arrangement instruction."""
        # Build exhibit list for context
        exhibit_list = "\n".join([
            f"{i}. {ex.get('name', ex.get('filename', 'Unknown'))} "
            f"(Criterion: {ex.get('criterion_letter', 'N/A')}, "
            f"Pages: {ex.get('page_count', '?')})"
            for i, ex in enumerate(exhibits)
        ])

        prompt = f"""You are an exhibit arrangement assistant for visa petitions.

CURRENT EXHIBIT ORDER (0-indexed):
{exhibit_list}

USER INSTRUCTION: "{instruction}"

Analyze this instruction and determine how to reorder the exhibits.
Return ONLY a valid JSON object (no markdown, no explanation) in this exact format:

{{"action": "reorder", "new_order": [list of indices], "explanation": "brief explanation"}}

Rules:
- "new_order" must contain ALL indices from 0 to {len(exhibits) - 1}
- Each index can only appear once
- Use the exact indices from the current order

Examples:
- "Put passport first" → find passport, move its index to position 0
- "Sort by page count" → reorder indices by page_count descending
- "Group awards together" → keep award items adjacent
- "Move item 3 to position 1" → reorder so index 3 becomes position 1

If you cannot understand the instruction, return:
{{"action": "unknown", "new_order": {list(range(len(exhibits)))}, "explanation": "Could not understand instruction"}}
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        text = response.content[0].text.strip()

        # Clean up response (remove markdown if present)
        if text.startswith("```"):
            text = re.sub(r'^```json?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

        result = json.loads(text)

        # Validate new_order
        new_order = result.get("new_order", list(range(len(exhibits))))
        if len(new_order) != len(exhibits):
            raise ValueError("new_order length mismatch")
        if set(new_order) != set(range(len(exhibits))):
            raise ValueError("new_order contains invalid indices")

        return {
            "action": result.get("action", "reorder"),
            "new_order": new_order,
            "explanation": result.get("explanation", "Rearranged as requested"),
            "method": "claude"
        }

    def _parse_with_rules(
        self,
        instruction: str,
        exhibits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Rule-based parsing fallback."""
        instruction_lower = instruction.lower()
        indices = list(range(len(exhibits)))

        # Sort by name (A-Z)
        if "a-z" in instruction_lower or "alphabetic" in instruction_lower or "by name" in instruction_lower:
            sorted_pairs = sorted(enumerate(exhibits), key=lambda x: x[1].get("name", "").lower())
            return {
                "action": "sort",
                "new_order": [p[0] for p in sorted_pairs],
                "explanation": "Sorted alphabetically by name",
                "method": "rules"
            }

        # Sort by page count
        if "page" in instruction_lower and "sort" in instruction_lower:
            sorted_pairs = sorted(enumerate(exhibits), key=lambda x: x[1].get("page_count", 0), reverse=True)
            return {
                "action": "sort",
                "new_order": [p[0] for p in sorted_pairs],
                "explanation": "Sorted by page count (highest first)",
                "method": "rules"
            }

        # Sort by criterion
        if "criterion" in instruction_lower or "criteria" in instruction_lower:
            sorted_pairs = sorted(enumerate(exhibits), key=lambda x: x[1].get("criterion_letter", "ZZZ"))
            return {
                "action": "sort",
                "new_order": [p[0] for p in sorted_pairs],
                "explanation": "Sorted by criterion letter",
                "method": "rules"
            }

        # Put X first
        first_match = re.search(r"put\s+(.+?)\s+first", instruction_lower)
        if first_match:
            search_term = first_match.group(1)
            for i, ex in enumerate(exhibits):
                name = ex.get("name", "").lower()
                if search_term in name:
                    indices.remove(i)
                    indices.insert(0, i)
                    return {
                        "action": "move",
                        "new_order": indices,
                        "explanation": f"Moved '{ex.get('name', '')}' to first position",
                        "method": "rules"
                    }

        # Move X before Y
        before_match = re.search(r"move\s+(.+?)\s+before\s+(.+)", instruction_lower)
        if before_match:
            item_to_move = before_match.group(1)
            target_item = before_match.group(2)

            move_idx = None
            target_idx = None

            for i, ex in enumerate(exhibits):
                name = ex.get("name", "").lower()
                if item_to_move in name and move_idx is None:
                    move_idx = i
                if target_item in name and target_idx is None:
                    target_idx = i

            if move_idx is not None and target_idx is not None:
                indices.remove(move_idx)
                insert_pos = indices.index(target_idx) if target_idx in indices else 0
                indices.insert(insert_pos, move_idx)
                return {
                    "action": "move",
                    "new_order": indices,
                    "explanation": f"Moved item before target",
                    "method": "rules"
                }

        # Reverse order
        if "reverse" in instruction_lower:
            return {
                "action": "reverse",
                "new_order": list(reversed(indices)),
                "explanation": "Reversed exhibit order",
                "method": "rules"
            }

        # Could not parse
        return {
            "action": "unknown",
            "new_order": indices,
            "explanation": "Could not understand instruction. Try: 'sort by name', 'put passport first', or 'reverse order'",
            "method": "rules"
        }


def render_arrangement_chat(
    exhibits: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Render chat interface for arrangement instructions.

    Args:
        exhibits: Current exhibit list
        api_key: Optional Anthropic API key

    Returns:
        Updated exhibit list (may be reordered)
    """
    st.markdown("### 💬 Arrangement Assistant")
    st.caption("Describe how you want to arrange the exhibits")

    # Initialize chat history
    if "arrangement_chat_history" not in st.session_state:
        st.session_state.arrangement_chat_history = []

    # Display chat history
    for msg in st.session_state.arrangement_chat_history:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # Chat input
    instruction = st.chat_input(
        placeholder="e.g., 'Put passport first, then forms, then awards'"
    )

    if instruction:
        # Add user message
        st.session_state.arrangement_chat_history.append({
            "role": "user",
            "content": instruction
        })
        st.chat_message("user").write(instruction)

        # Process instruction
        with st.spinner("Rearranging exhibits..."):
            chat = ArrangementChat(api_key)
            result = chat.parse_instruction(instruction, exhibits)

        # Apply new order if successful
        if result["action"] != "unknown":
            new_exhibits = [exhibits[i] for i in result["new_order"]]

            # Update exhibit numbers
            for i, ex in enumerate(new_exhibits):
                ex["exhibit_number"] = chr(65 + i) if i < 26 else f"A{chr(65 + i - 26)}"

            response = f"✅ {result['explanation']}"
            st.session_state.arrangement_chat_history.append({
                "role": "assistant",
                "content": response
            })
            st.chat_message("assistant").write(response)

            # Update session state
            st.session_state.exhibit_order = new_exhibits
            return new_exhibits

        else:
            response = f"❓ {result['explanation']}"
            st.session_state.arrangement_chat_history.append({
                "role": "assistant",
                "content": response
            })
            st.chat_message("assistant").write(response)

    return exhibits


def render_quick_commands() -> Optional[str]:
    """
    Render quick command buttons.

    Returns:
        Selected command string or None
    """
    st.markdown("**Quick Commands:**")

    cols = st.columns(4)

    commands = [
        ("📝 A-Z", "Sort alphabetically by name"),
        ("📊 By Criterion", "Group exhibits by criterion letter"),
        ("📄 By Pages", "Sort by page count (largest first)"),
        ("↩️ Reverse", "Reverse the current order")
    ]

    for i, (label, command) in enumerate(commands):
        with cols[i]:
            if st.button(label, key=f"quick_cmd_{i}"):
                return command

    return None


def get_suggested_instructions(visa_type: str) -> List[str]:
    """
    Get suggested arrangement instructions based on visa type.

    Args:
        visa_type: Visa type (O-1A, P-1A, etc.)

    Returns:
        List of suggested instruction strings
    """
    base_suggestions = [
        "Put passport first, then CV, then forms",
        "Group all award documents together",
        "Sort by criterion letter",
        "Put expert letters at the end"
    ]

    visa_specific = {
        "O-1A": [
            "Put administrative docs first, then criterion evidence by letter A-H",
            "Group all media articles together after awards"
        ],
        "P-1A": [
            "Put contract and itinerary first after forms",
            "Group all athletic achievements together"
        ],
        "EB-1A": [
            "Order exhibits to match petition letter criteria order",
            "Put original contributions evidence prominently"
        ]
    }

    return base_suggestions + visa_specific.get(visa_type, [])
