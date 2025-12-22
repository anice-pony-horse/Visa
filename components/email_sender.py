"""
Email Sender Component (Feature 8)
===================================

Email notification on completion.
- SMTP (Gmail) support
- SendGrid support
- Attachment handling (under 25MB)
- Case summary in email
"""

import streamlit as st
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders


@dataclass
class EmailConfig:
    """Email configuration"""
    provider: str = "smtp"  # smtp, sendgrid
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    sendgrid_api_key: str = ""
    from_email: str = ""
    from_name: str = "Visa Exhibit Generator"


@dataclass
class EmailMessage:
    """Email message"""
    to: str
    cc: Optional[List[str]] = None
    subject: str = ""
    body: str = ""
    html_body: Optional[str] = None
    attachment_path: Optional[str] = None
    attachment_name: Optional[str] = None


class EmailSender:
    """Email sender with SMTP and SendGrid support"""

    def __init__(self, config: Optional[EmailConfig] = None):
        """Initialize email sender"""
        self.config = config or self._load_config()

    def _load_config(self) -> EmailConfig:
        """Load config from environment or secrets"""
        return EmailConfig(
            provider=os.getenv('EMAIL_PROVIDER', 'smtp'),
            smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            smtp_user=os.getenv('SMTP_USER', ''),
            smtp_password=os.getenv('SMTP_PASSWORD', ''),
            sendgrid_api_key=os.getenv('SENDGRID_API_KEY', ''),
            from_email=os.getenv('EMAIL_FROM', ''),
            from_name=os.getenv('EMAIL_FROM_NAME', 'Visa Exhibit Generator')
        )

    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """
        Send an email.

        Returns:
            Dict with 'success' and 'error' keys
        """
        if self.config.provider == "sendgrid":
            return self._send_sendgrid(message)
        else:
            return self._send_smtp(message)

    def _send_smtp(self, message: EmailMessage) -> Dict[str, Any]:
        """Send via SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
            msg['To'] = message.to
            if message.cc:
                msg['Cc'] = ", ".join(message.cc)
            msg['Subject'] = message.subject

            # Body
            if message.html_body:
                msg.attach(MIMEText(message.html_body, 'html'))
            else:
                msg.attach(MIMEText(message.body, 'plain'))

            # Attachment
            if message.attachment_path and os.path.exists(message.attachment_path):
                file_size = os.path.getsize(message.attachment_path)
                if file_size < 25 * 1024 * 1024:  # 25MB limit
                    with open(message.attachment_path, 'rb') as f:
                        part = MIMEBase('application', 'pdf')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = message.attachment_name or os.path.basename(message.attachment_path)
                        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                        msg.attach(part)

            # Send
            recipients = [message.to] + (message.cc or [])

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg, to_addrs=recipients)

            return {'success': True, 'error': None}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _send_sendgrid(self, message: EmailMessage) -> Dict[str, Any]:
        """Send via SendGrid"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType

            mail = Mail(
                from_email=(self.config.from_email, self.config.from_name),
                to_emails=message.to,
                subject=message.subject,
                html_content=message.html_body or message.body
            )

            # Add CC
            if message.cc:
                for cc in message.cc:
                    mail.add_cc(cc)

            # Add attachment
            if message.attachment_path and os.path.exists(message.attachment_path):
                file_size = os.path.getsize(message.attachment_path)
                if file_size < 25 * 1024 * 1024:
                    import base64
                    with open(message.attachment_path, 'rb') as f:
                        data = base64.b64encode(f.read()).decode()

                    attachment = Attachment(
                        FileContent(data),
                        FileName(message.attachment_name or os.path.basename(message.attachment_path)),
                        FileType('application/pdf')
                    )
                    mail.add_attachment(attachment)

            sg = SendGridAPIClient(self.config.sendgrid_api_key)
            response = sg.send(mail)

            return {
                'success': response.status_code in [200, 201, 202],
                'error': None if response.status_code in [200, 201, 202] else f"Status: {response.status_code}"
            }

        except ImportError:
            return {'success': False, 'error': 'SendGrid package not installed. Run: pip install sendgrid'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


def send_completion_email(
    recipient: str,
    case_info: Dict[str, Any],
    file_path: Optional[str] = None,
    download_link: Optional[str] = None,
    cc_emails: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send completion notification email.

    Args:
        recipient: Email address to send to
        case_info: Case information dictionary
        file_path: Path to exhibit package PDF
        download_link: Optional download link
        cc_emails: Optional CC recipients

    Returns:
        Dict with 'success' and 'error' keys
    """
    # Build email body
    beneficiary = case_info.get('beneficiary_name', 'N/A')
    petitioner = case_info.get('petitioner_name', 'N/A')
    visa_type = case_info.get('visa_type', 'N/A')
    processing = case_info.get('processing_type', 'Regular')
    exhibit_count = case_info.get('exhibit_count', 0)
    page_count = case_info.get('page_count', 0)

    subject = f"Visa Exhibit Package Ready - {beneficiary}"

    body = f"""
Your visa exhibit package has been generated successfully.

Case Details:
- Beneficiary: {beneficiary}
- Petitioner: {petitioner}
- Visa Type: {visa_type}
- Processing: {processing}
- Exhibits: {exhibit_count}
- Total Pages: {page_count}

{f"Download Link: {download_link}" if download_link else ""}

This email was sent automatically by the Visa Exhibit Generator.
    """.strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1f77b4; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .case-details {{ background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .case-details table {{ width: 100%; border-collapse: collapse; }}
        .case-details td {{ padding: 8px; border-bottom: 1px solid #eee; }}
        .case-details td:first-child {{ font-weight: bold; width: 40%; }}
        .download-btn {{ display: inline-block; background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Visa Exhibit Package Ready</h1>
        </div>
        <div class="content">
            <p>Your visa exhibit package has been generated successfully.</p>

            <div class="case-details">
                <table>
                    <tr><td>Beneficiary</td><td>{beneficiary}</td></tr>
                    <tr><td>Petitioner</td><td>{petitioner}</td></tr>
                    <tr><td>Visa Type</td><td>{visa_type}</td></tr>
                    <tr><td>Processing</td><td>{processing}</td></tr>
                    <tr><td>Exhibits</td><td>{exhibit_count}</td></tr>
                    <tr><td>Total Pages</td><td>{page_count}</td></tr>
                </table>
            </div>

            {f'<a href="{download_link}" class="download-btn">Download Exhibit Package</a>' if download_link else ''}

        </div>
        <div class="footer">
            This email was sent automatically by the Visa Exhibit Generator.
        </div>
    </div>
</body>
</html>
    """

    message = EmailMessage(
        to=recipient,
        cc=cc_emails,
        subject=subject,
        body=body,
        html_body=html_body,
        attachment_path=file_path,
        attachment_name=f"Exhibit_Package_{beneficiary.replace(' ', '_')}.pdf" if beneficiary != 'N/A' else None
    )

    sender = EmailSender()
    return sender.send(message)


def render_email_form(
    case_info: Dict[str, Any],
    file_path: Optional[str] = None,
    download_link: Optional[str] = None
):
    """Render email notification form"""
    st.subheader("📧 Email Notification")

    with st.expander("Send completion email", expanded=False):
        recipient = st.text_input(
            "Recipient Email",
            placeholder="attorney@lawfirm.com",
            key="email_recipient"
        )

        cc_input = st.text_input(
            "CC (comma-separated)",
            placeholder="paralegal@lawfirm.com, manager@lawfirm.com",
            key="email_cc"
        )

        cc_emails = [e.strip() for e in cc_input.split(',') if e.strip()] if cc_input else None

        # Preview
        beneficiary = case_info.get('beneficiary_name', 'N/A')
        st.info(f"Subject: Visa Exhibit Package Ready - {beneficiary}")

        # Attachment info
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            if file_size < 25:
                st.success(f"PDF will be attached ({file_size:.1f} MB)")
            else:
                st.warning(f"PDF too large to attach ({file_size:.1f} MB > 25 MB limit)")

        if st.button("Send Email", type="primary", disabled=not recipient):
            with st.spinner("Sending email..."):
                result = send_completion_email(
                    recipient=recipient,
                    case_info=case_info,
                    file_path=file_path if file_path and os.path.getsize(file_path) < 25 * 1024 * 1024 else None,
                    download_link=download_link,
                    cc_emails=cc_emails
                )

                if result['success']:
                    st.success(f"Email sent to {recipient}")
                else:
                    st.error(f"Failed to send email: {result['error']}")


def render_email_config():
    """Render email configuration form (for sidebar)"""
    with st.expander("📧 Email Configuration"):
        provider = st.selectbox(
            "Email Provider",
            options=["SMTP (Gmail)", "SendGrid"],
            key="email_provider_select"
        )

        if provider == "SMTP (Gmail)":
            st.text_input("SMTP Server", value="smtp.gmail.com", key="smtp_server")
            st.number_input("SMTP Port", value=587, key="smtp_port")
            st.text_input("Email Address", key="smtp_user")
            st.text_input("App Password", type="password", key="smtp_password",
                         help="For Gmail, use App Password (not regular password)")
        else:
            st.text_input("SendGrid API Key", type="password", key="sendgrid_key")
            st.text_input("From Email", key="sendgrid_from")

        st.caption("Settings are stored in session only")
