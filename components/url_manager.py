"""
URL Manager Component (Feature 2)
=================================

Drag-and-drop URL list with tagging.
- Textarea for pasting multiple URLs
- Sortable drag-drop list
- Tag dropdown per item
- Batch tagging support
"""

import streamlit as st
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
import requests
from urllib.parse import urlparse


# Document tags for categorization
DOCUMENT_TAGS = [
    "Forms",
    "Brief",
    "Evidence",
    "Credentials",
    "Letters",
    "Awards",
    "Media",
    "Judging",
    "Contributions",
    "Published",
    "Memberships",
    "Salary",
    "Critical Role",
    "Other"
]


@dataclass
class URLItem:
    """Represents a URL item in the list"""
    id: str
    url: str
    title: str
    tag: str = "Other"
    order: int = 0
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'tag': self.tag,
            'order': self.order,
            'added_at': self.added_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'URLItem':
        return cls(**data)


class URLManager:
    """Manages URL list with drag-and-drop functionality"""

    def __init__(self):
        """Initialize URL manager"""
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state"""
        if 'url_list' not in st.session_state:
            st.session_state.url_list = []
        if 'url_counter' not in st.session_state:
            st.session_state.url_counter = 0

    @property
    def urls(self) -> List[URLItem]:
        """Get current URL list"""
        return [URLItem.from_dict(u) if isinstance(u, dict) else u
                for u in st.session_state.url_list]

    def add_url(self, url: str, title: Optional[str] = None, tag: str = "Other") -> URLItem:
        """Add a URL to the list"""
        st.session_state.url_counter += 1
        item = URLItem(
            id=f"url_{st.session_state.url_counter}",
            url=url.strip(),
            title=title or self._extract_title(url),
            tag=tag,
            order=len(st.session_state.url_list)
        )
        st.session_state.url_list.append(item.to_dict())
        return item

    def add_urls_batch(self, urls_text: str) -> List[URLItem]:
        """Add multiple URLs from text (one per line)"""
        added = []
        lines = urls_text.strip().split('\n')
        for line in lines:
            url = line.strip()
            if url and self._is_valid_url(url):
                item = self.add_url(url)
                added.append(item)
        return added

    def remove_url(self, url_id: str):
        """Remove a URL by ID"""
        st.session_state.url_list = [
            u for u in st.session_state.url_list
            if (u.get('id') if isinstance(u, dict) else u.id) != url_id
        ]
        self._reorder()

    def update_url(self, url_id: str, **kwargs):
        """Update URL properties"""
        for i, u in enumerate(st.session_state.url_list):
            item_id = u.get('id') if isinstance(u, dict) else u.id
            if item_id == url_id:
                if isinstance(u, dict):
                    u.update(kwargs)
                else:
                    for k, v in kwargs.items():
                        setattr(u, k, v)
                    st.session_state.url_list[i] = u.to_dict()
                break

    def reorder(self, new_order: List[str]):
        """Reorder URLs based on list of IDs"""
        id_to_item = {
            (u.get('id') if isinstance(u, dict) else u.id): u
            for u in st.session_state.url_list
        }
        st.session_state.url_list = [id_to_item[uid] for uid in new_order if uid in id_to_item]
        self._reorder()

    def _reorder(self):
        """Update order field for all items"""
        for i, u in enumerate(st.session_state.url_list):
            if isinstance(u, dict):
                u['order'] = i
            else:
                u.order = i
                st.session_state.url_list[i] = u.to_dict()

    def clear_all(self):
        """Clear all URLs"""
        st.session_state.url_list = []

    def batch_tag(self, url_ids: List[str], tag: str):
        """Apply tag to multiple URLs"""
        for url_id in url_ids:
            self.update_url(url_id, tag=tag)

    def _is_valid_url(self, url: str) -> bool:
        """Check if string is a valid URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _extract_title(self, url: str) -> str:
        """Extract a title from URL (domain + path)"""
        try:
            parsed = urlparse(url)
            # Get domain without www
            domain = parsed.netloc.replace('www.', '')
            # Get last path segment
            path = parsed.path.rstrip('/').split('/')[-1] if parsed.path else ''
            # Clean up path
            path = path.replace('-', ' ').replace('_', ' ')
            path = re.sub(r'\.(pdf|html|htm|php|aspx?)$', '', path, flags=re.I)

            if path:
                return f"{path} ({domain})"
            return domain
        except:
            return url[:50]

    def fetch_title(self, url: str) -> Optional[str]:
        """Fetch actual page title from URL (optional)"""
        try:
            response = requests.get(url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; ExhibitMaker/1.0)'
            })
            match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.I)
            if match:
                return match.group(1).strip()[:100]
        except:
            pass
        return None


def render_url_manager() -> List[URLItem]:
    """
    Render the URL manager interface.

    Returns:
        List of URLItem objects
    """
    manager = URLManager()

    st.subheader("📎 URL Documents")

    st.markdown("""
    <div style="background-color: #fff3cd; padding: 0.75rem; border-radius: 0.5rem; margin-bottom: 1rem;">
        <small>Paste URLs of online documents to include in your exhibit package.</small>
    </div>
    """, unsafe_allow_html=True)

    # URL Input Area
    with st.expander("➕ Add URLs", expanded=len(manager.urls) == 0):
        url_text = st.text_area(
            "Paste URLs (one per line)",
            placeholder="https://example.com/article.pdf\nhttps://news.com/press-release\nhttps://award-site.org/recognition",
            height=100,
            key="url_input_area"
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Add URLs", type="primary"):
                if url_text.strip():
                    added = manager.add_urls_batch(url_text)
                    if added:
                        st.success(f"Added {len(added)} URL(s)")
                        st.rerun()
                    else:
                        st.warning("No valid URLs found")

    # URL List Display
    if manager.urls:
        st.markdown("---")

        # Batch operations
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            if st.checkbox("Select All", key="select_all_urls"):
                st.session_state.selected_urls = [u.id for u in manager.urls]
            else:
                if 'selected_urls' not in st.session_state:
                    st.session_state.selected_urls = []

        with col2:
            batch_tag = st.selectbox(
                "Batch Tag",
                options=[""] + DOCUMENT_TAGS,
                key="batch_tag_select",
                label_visibility="collapsed"
            )

        with col3:
            if st.button("Apply Tag to Selected"):
                if batch_tag and st.session_state.get('selected_urls'):
                    manager.batch_tag(st.session_state.selected_urls, batch_tag)
                    st.rerun()

        with col4:
            if st.button("🗑️ Clear All"):
                manager.clear_all()
                st.rerun()

        st.markdown("---")

        # Sortable URL List
        # Note: For full drag-and-drop, we'd use streamlit-sortables
        # For now, using manual reorder buttons

        for i, item in enumerate(manager.urls):
            col1, col2, col3, col4, col5 = st.columns([0.5, 3, 2, 1, 0.5])

            with col1:
                # Selection checkbox
                selected = st.checkbox(
                    "",
                    value=item.id in st.session_state.get('selected_urls', []),
                    key=f"select_{item.id}",
                    label_visibility="collapsed"
                )
                if selected and item.id not in st.session_state.get('selected_urls', []):
                    st.session_state.setdefault('selected_urls', []).append(item.id)
                elif not selected and item.id in st.session_state.get('selected_urls', []):
                    st.session_state['selected_urls'].remove(item.id)

            with col2:
                # URL and title
                new_title = st.text_input(
                    "Title",
                    value=item.title,
                    key=f"title_{item.id}",
                    label_visibility="collapsed"
                )
                if new_title != item.title:
                    manager.update_url(item.id, title=new_title)

                # Show truncated URL
                st.caption(item.url[:60] + "..." if len(item.url) > 60 else item.url)

            with col3:
                # Tag dropdown
                current_tag_index = DOCUMENT_TAGS.index(item.tag) if item.tag in DOCUMENT_TAGS else len(DOCUMENT_TAGS) - 1
                new_tag = st.selectbox(
                    "Tag",
                    options=DOCUMENT_TAGS,
                    index=current_tag_index,
                    key=f"tag_{item.id}",
                    label_visibility="collapsed"
                )
                if new_tag != item.tag:
                    manager.update_url(item.id, tag=new_tag)

            with col4:
                # Reorder buttons
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if i > 0:
                        if st.button("↑", key=f"up_{item.id}"):
                            urls = manager.urls
                            ids = [u.id for u in urls]
                            idx = ids.index(item.id)
                            ids[idx], ids[idx-1] = ids[idx-1], ids[idx]
                            manager.reorder(ids)
                            st.rerun()
                with btn_col2:
                    if i < len(manager.urls) - 1:
                        if st.button("↓", key=f"down_{item.id}"):
                            urls = manager.urls
                            ids = [u.id for u in urls]
                            idx = ids.index(item.id)
                            ids[idx], ids[idx+1] = ids[idx+1], ids[idx]
                            manager.reorder(ids)
                            st.rerun()

            with col5:
                # Delete button
                if st.button("✕", key=f"delete_{item.id}"):
                    manager.remove_url(item.id)
                    st.rerun()

            st.markdown("---")

        # Summary
        st.info(f"📊 {len(manager.urls)} URL(s) added")

    return manager.urls


def get_url_list() -> List[URLItem]:
    """Get the current URL list from session state"""
    manager = URLManager()
    return manager.urls
