"""
Configuration Management
========================

Environment configuration for Visa Exhibit Generator V2.0.
Supports local development and production deployment.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class Config:
    """Application configuration"""

    # App settings
    app_name: str = "Visa Exhibit Generator V2.0"
    app_version: str = "2.0.0"
    debug: bool = False

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""  # anon key
    supabase_service_key: str = ""  # service role key (server-side only)

    # Anthropic AI
    anthropic_api_key: str = ""

    # Email (SMTP)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Email (SendGrid)
    sendgrid_api_key: str = ""
    email_from: str = ""
    email_from_name: str = "Visa Exhibit Generator"

    # Google Drive
    google_client_id: str = ""
    google_client_secret: str = ""

    # SmallPDF
    smallpdf_api_key: str = ""

    # App URL (for shareable links)
    app_base_url: str = "http://localhost:8501"

    # Storage
    temp_dir: str = ""
    max_upload_size_mb: int = 100
    max_attachment_size_mb: int = 25

    # Feature flags
    enable_ai_classification: bool = True
    enable_compression: bool = True
    enable_email: bool = True
    enable_shareable_links: bool = True
    enable_google_drive: bool = True

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables"""
        return cls(
            # App settings
            app_name=os.getenv('APP_NAME', cls.app_name),
            app_version=os.getenv('APP_VERSION', cls.app_version),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',

            # Supabase
            supabase_url=os.getenv('SUPABASE_URL', ''),
            supabase_key=os.getenv('SUPABASE_KEY', ''),
            supabase_service_key=os.getenv('SUPABASE_SERVICE_KEY', ''),

            # Anthropic
            anthropic_api_key=os.getenv('ANTHROPIC_API_KEY', ''),

            # Email SMTP
            smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            smtp_user=os.getenv('SMTP_USER', ''),
            smtp_password=os.getenv('SMTP_PASSWORD', ''),

            # Email SendGrid
            sendgrid_api_key=os.getenv('SENDGRID_API_KEY', ''),
            email_from=os.getenv('EMAIL_FROM', ''),
            email_from_name=os.getenv('EMAIL_FROM_NAME', 'Visa Exhibit Generator'),

            # Google Drive
            google_client_id=os.getenv('GOOGLE_CLIENT_ID', ''),
            google_client_secret=os.getenv('GOOGLE_CLIENT_SECRET', ''),

            # SmallPDF
            smallpdf_api_key=os.getenv('SMALLPDF_API_KEY', ''),

            # App URL
            app_base_url=os.getenv('APP_BASE_URL', 'http://localhost:8501'),

            # Storage
            temp_dir=os.getenv('TEMP_DIR', ''),
            max_upload_size_mb=int(os.getenv('MAX_UPLOAD_SIZE_MB', '100')),
            max_attachment_size_mb=int(os.getenv('MAX_ATTACHMENT_SIZE_MB', '25')),

            # Feature flags
            enable_ai_classification=os.getenv('ENABLE_AI_CLASSIFICATION', 'true').lower() == 'true',
            enable_compression=os.getenv('ENABLE_COMPRESSION', 'true').lower() == 'true',
            enable_email=os.getenv('ENABLE_EMAIL', 'true').lower() == 'true',
            enable_shareable_links=os.getenv('ENABLE_SHAREABLE_LINKS', 'true').lower() == 'true',
            enable_google_drive=os.getenv('ENABLE_GOOGLE_DRIVE', 'true').lower() == 'true',
        )

    @classmethod
    def from_streamlit_secrets(cls) -> 'Config':
        """Load configuration from Streamlit secrets"""
        try:
            import streamlit as st

            return cls(
                # Supabase
                supabase_url=st.secrets.get('SUPABASE_URL', ''),
                supabase_key=st.secrets.get('SUPABASE_KEY', ''),
                supabase_service_key=st.secrets.get('SUPABASE_SERVICE_KEY', ''),

                # Anthropic
                anthropic_api_key=st.secrets.get('ANTHROPIC_API_KEY', ''),

                # Email
                smtp_server=st.secrets.get('SMTP_SERVER', 'smtp.gmail.com'),
                smtp_port=int(st.secrets.get('SMTP_PORT', 587)),
                smtp_user=st.secrets.get('SMTP_USER', ''),
                smtp_password=st.secrets.get('SMTP_PASSWORD', ''),
                sendgrid_api_key=st.secrets.get('SENDGRID_API_KEY', ''),
                email_from=st.secrets.get('EMAIL_FROM', ''),

                # Google Drive
                google_client_id=st.secrets.get('GOOGLE_CLIENT_ID', ''),
                google_client_secret=st.secrets.get('GOOGLE_CLIENT_SECRET', ''),

                # SmallPDF
                smallpdf_api_key=st.secrets.get('SMALLPDF_API_KEY', ''),

                # App URL
                app_base_url=st.secrets.get('APP_BASE_URL', 'http://localhost:8501'),
            )
        except Exception:
            return cls.from_env()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive keys)"""
        return {
            'app_name': self.app_name,
            'app_version': self.app_version,
            'debug': self.debug,
            'supabase_url': self.supabase_url,
            'app_base_url': self.app_base_url,
            'max_upload_size_mb': self.max_upload_size_mb,
            'max_attachment_size_mb': self.max_attachment_size_mb,
            'enable_ai_classification': self.enable_ai_classification,
            'enable_compression': self.enable_compression,
            'enable_email': self.enable_email,
            'enable_shareable_links': self.enable_shareable_links,
            'enable_google_drive': self.enable_google_drive,
            # Don't expose API keys
            'has_supabase_key': bool(self.supabase_key),
            'has_anthropic_key': bool(self.anthropic_api_key),
            'has_sendgrid_key': bool(self.sendgrid_api_key),
            'has_google_credentials': bool(self.google_client_id),
        }


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        # Try Streamlit secrets first, then environment
        try:
            _config = Config.from_streamlit_secrets()
        except Exception:
            _config = Config.from_env()
    return _config


def reload_config():
    """Reload configuration from environment"""
    global _config
    _config = None
    return get_config()
