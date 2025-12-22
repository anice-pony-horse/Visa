"""
Link Generator Component (Feature 6)
=====================================

Shareable link generation with QR codes.
- Temporary download URLs
- Expiration options
- Password protection
- QR code generation
"""

import streamlit as st
from dataclasses import dataclass
from typing import Optional, Dict, Any
import os
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
import json


@dataclass
class ShareableLink:
    """Shareable link data"""
    link_id: str
    url: str
    file_path: str
    created_at: str
    expires_at: Optional[str]
    password_hash: Optional[str]
    access_count: int = 0
    max_access: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'link_id': self.link_id,
            'url': self.url,
            'file_path': self.file_path,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'password_hash': self.password_hash,
            'access_count': self.access_count,
            'max_access': self.max_access
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShareableLink':
        return cls(**data)

    def is_expired(self) -> bool:
        """Check if link has expired"""
        if not self.expires_at:
            return False
        return datetime.now() > datetime.fromisoformat(self.expires_at)

    def is_access_exceeded(self) -> bool:
        """Check if max access count exceeded"""
        if not self.max_access:
            return False
        return self.access_count >= self.max_access

    def verify_password(self, password: str) -> bool:
        """Verify password"""
        if not self.password_hash:
            return True
        return hashlib.sha256(password.encode()).hexdigest() == self.password_hash


class LinkGenerator:
    """Generate shareable download links"""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize link generator"""
        self.base_url = base_url or os.getenv('APP_BASE_URL', 'http://localhost:8501')
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state"""
        if 'shareable_links' not in st.session_state:
            st.session_state.shareable_links = {}

    def generate_link(
        self,
        file_path: str,
        expires_in: Optional[str] = "24h",
        password: Optional[str] = None,
        max_access: Optional[int] = None
    ) -> ShareableLink:
        """
        Generate a shareable link.

        Args:
            file_path: Path to file
            expires_in: Expiration time (1h, 24h, 7d, never)
            password: Optional password
            max_access: Optional max access count

        Returns:
            ShareableLink object
        """
        # Generate unique ID
        link_id = secrets.token_urlsafe(16)

        # Calculate expiration
        expires_at = None
        if expires_in and expires_in != "never":
            now = datetime.now()
            if expires_in == "1h":
                expires_at = now + timedelta(hours=1)
            elif expires_in == "24h":
                expires_at = now + timedelta(hours=24)
            elif expires_in == "7d":
                expires_at = now + timedelta(days=7)

        # Hash password
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Create link
        link = ShareableLink(
            link_id=link_id,
            url=f"{self.base_url}/download/{link_id}",
            file_path=file_path,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at.isoformat() if expires_at else None,
            password_hash=password_hash,
            access_count=0,
            max_access=max_access
        )

        # Store in session
        st.session_state.shareable_links[link_id] = link.to_dict()

        return link

    def get_link(self, link_id: str) -> Optional[ShareableLink]:
        """Get link by ID"""
        data = st.session_state.shareable_links.get(link_id)
        if data:
            return ShareableLink.from_dict(data)
        return None

    def increment_access(self, link_id: str):
        """Increment access count"""
        if link_id in st.session_state.shareable_links:
            st.session_state.shareable_links[link_id]['access_count'] += 1

    def delete_link(self, link_id: str):
        """Delete a link"""
        if link_id in st.session_state.shareable_links:
            del st.session_state.shareable_links[link_id]


def generate_qr_code(url: str, size: int = 200) -> Optional[bytes]:
    """
    Generate QR code image.

    Args:
        url: URL to encode
        size: Size in pixels

    Returns:
        PNG image bytes or None if qrcode not installed
    """
    try:
        import qrcode
        from io import BytesIO

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Resize if needed
        img = img.resize((size, size))

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    except ImportError:
        return None


def generate_shareable_link(
    file_path: str,
    expires_in: str = "24h",
    password: Optional[str] = None
) -> ShareableLink:
    """
    Convenience function to generate shareable link.

    Args:
        file_path: Path to file
        expires_in: Expiration time
        password: Optional password

    Returns:
        ShareableLink object
    """
    generator = LinkGenerator()
    return generator.generate_link(file_path, expires_in, password)


def render_link_generator(file_path: str):
    """Render the link generator UI"""
    st.subheader("🔗 Shareable Link")

    generator = LinkGenerator()

    # Check if link already exists
    existing_link = None
    for link_id, link_data in st.session_state.get('shareable_links', {}).items():
        if link_data.get('file_path') == file_path:
            existing_link = ShareableLink.from_dict(link_data)
            break

    if existing_link and not existing_link.is_expired():
        # Show existing link
        st.success("Link generated!")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.text_input("Share this link", value=existing_link.url, key="share_url")

            # Copy button (JavaScript)
            st.markdown(f"""
            <button onclick="navigator.clipboard.writeText('{existing_link.url}')"
                    style="background:#1f77b4; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">
                Copy Link
            </button>
            """, unsafe_allow_html=True)

        with col2:
            # QR Code
            qr_bytes = generate_qr_code(existing_link.url)
            if qr_bytes:
                st.image(qr_bytes, caption="Scan to download", width=150)
            else:
                st.info("Install qrcode for QR: pip install qrcode pillow")

        # Link info
        with st.expander("Link details"):
            st.write(f"**Created**: {existing_link.created_at}")
            if existing_link.expires_at:
                st.write(f"**Expires**: {existing_link.expires_at}")
            else:
                st.write("**Expires**: Never")
            st.write(f"**Access count**: {existing_link.access_count}")
            if existing_link.password_hash:
                st.write("**Password protected**: Yes")

            if st.button("Delete link"):
                generator.delete_link(existing_link.link_id)
                st.rerun()

    else:
        # Generate new link
        with st.expander("Generate shareable link", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                expires_in = st.selectbox(
                    "Expires in",
                    options=["1h", "24h", "7d", "never"],
                    index=1,
                    format_func=lambda x: {
                        "1h": "1 hour",
                        "24h": "24 hours",
                        "7d": "7 days",
                        "never": "Never"
                    }.get(x, x)
                )

            with col2:
                password = st.text_input(
                    "Password (optional)",
                    type="password",
                    help="Leave empty for no password"
                )

            if st.button("Generate Link", type="primary"):
                link = generator.generate_link(
                    file_path=file_path,
                    expires_in=expires_in,
                    password=password if password else None
                )
                st.rerun()


def render_download_page(link_id: str):
    """
    Render download page for shareable link.
    This would be a separate route in production.
    """
    generator = LinkGenerator()
    link = generator.get_link(link_id)

    if not link:
        st.error("Link not found")
        return

    if link.is_expired():
        st.error("This link has expired")
        return

    if link.is_access_exceeded():
        st.error("This link has reached its maximum access count")
        return

    # Password check
    if link.password_hash:
        password = st.text_input("Enter password", type="password")
        if st.button("Submit"):
            if link.verify_password(password):
                generator.increment_access(link_id)
                with open(link.file_path, 'rb') as f:
                    st.download_button(
                        "Download",
                        data=f,
                        file_name=os.path.basename(link.file_path),
                        mime="application/pdf"
                    )
            else:
                st.error("Incorrect password")
    else:
        generator.increment_access(link_id)
        if os.path.exists(link.file_path):
            with open(link.file_path, 'rb') as f:
                st.download_button(
                    "Download Exhibit Package",
                    data=f,
                    file_name=os.path.basename(link.file_path),
                    mime="application/pdf",
                    type="primary"
                )
        else:
            st.error("File not found")
