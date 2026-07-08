from __future__ import annotations

import mimetypes
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shared import SharedSettings
from shared.logger import LoggerFactory

from .settings import EmailSettings

if TYPE_CHECKING:
    import io
    from logging import Logger

    from nepalidates import FilingMonth
    from reporting.models import CompanyInfo

logger = LoggerFactory.get_logger(__name__)


def send_vat_report_email(
    filing_month: FilingMonth,
    company_info: CompanyInfo,
    exported_excel_reports: dict[Any, io.BytesIO],
    analytics_html_content: str,
) -> None:
    """
    Sends an email with VAT reports (Excel) and optional HTML analytics as attachments.

    Args:
        filing_month (FilingMonth): The filing month object.
        company_info (CompanyInfo): The company information.
        exported_excel_reports (dict[Any, io.BytesIO]): Dictionary of report_type to BytesIO buffers.
        analytics_html_content (str | None): The HTML content to be used as the email body.

    """
    settings = EmailSettings()
    shared_settings = SharedSettings()

    if not exported_excel_reports and not analytics_html_content:
        logger.info(
            "No reports to attach and no analytics HTML content for the body. Skipping email.",
        )
        return

    subject = (
        f"{shared_settings.EMAIL_SUBJECT_PREFIX}"
        f"{filing_month.name} {filing_month.fiscal_year} BS - "
        f"{company_info.office_name} ({company_info.pan_no})"
    )

    attachments_to_send: list[tuple[Path, io.BytesIO]] = []

    for rtype, buffer in exported_excel_reports.items():
        # Create a dummy Path object for the attachment function
        attachment_path = Path(
            f"{rtype.name} - {filing_month.name}{rtype.file_extension}",
        )
        attachments_to_send.append((attachment_path, buffer))

    try:
        _send_email_with_attachments(
            subject=subject,
            html_body=analytics_html_content,
            attachments=attachments_to_send,
            sender_email=settings.SENDER,  # Use SENDER from SharedSettings
            recipient_emails=settings.RECIPIENTS,  # Use RECIPIENTS from SharedSettings
            logger_instance=logger,
        )
        logger.info("VAT report email sent successfully for %s.", filing_month.name)
    except Exception as e:
        logger.exception("Failed to send VAT report email for %s.", filing_month.name)
        msg = f"VAT report email failed: {e}"
        raise RuntimeError(msg) from e


def _send_email_with_attachments(
    subject: str,
    html_body: str,
    attachments: list[tuple[Path, io.BytesIO]],
    *,
    sender_email: str | None = None,
    recipient_emails: list[str] | None = None,
    logger_instance: Logger = logger,
) -> None:
    """Internal helper to send an email with an HTML body and multiple file attachments."""
    settings = EmailSettings()

    sender = sender_email if sender_email else settings.SENDER
    recipients = recipient_emails if recipient_emails else settings.RECIPIENTS

    if not sender or not recipients:
        logger_instance.error(
            "Email sender (%s) or recipients (%s) are not configured.",
            sender,
            recipients,
        )
        msg = "Email sender or recipients not configured."
        raise ValueError(msg)

    logger_instance.info(
        "Attempting to send email to %s with subject: '%s'",
        ", ".join(recipients),
        subject,
    )

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    for file_path, file_buffer in attachments:
        try:
            file_buffer.seek(0)  # Ensure buffer is at the start for reading

            # Guess MIME type based on file extension
            ctype, encoding = mimetypes.guess_type(file_path.name)
            if ctype is None or encoding is not None:
                # Fallback if guess fails or encoding is present (e.g., gzip)
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)

            part = MIMEBase(maintype, subtype)
            part.set_payload(file_buffer.read())
            encoders.encode_base64(part)  # Encode to base64 for email transport

            # Set Content-Disposition to allow attachments to be downloaded by filename
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {file_path.name}",
            )
            msg.attach(part)
            logger_instance.debug("Attached file: '%s'", file_path.name)

        except Exception:
            logger_instance.exception(
                "Failed to attach file '%s'. Skipping.",
                file_path.name,
            )

    try:
        # Connect to SMTP server
        if settings.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            if settings.SMTP_USE_TLS:
                server.starttls()  # Upgrade connection to TLS

        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(sender, recipients, text)
        server.quit()
        logger_instance.info("Email sent successfully!")

    except smtplib.SMTPAuthenticationError:
        logger_instance.exception(
            "SMTP Authentication Error: Check username and password for '%s'.",
            settings.SMTP_USERNAME,
        )
        raise
    except smtplib.SMTPConnectError:
        logger_instance.exception(
            "SMTP Connection Error: Could not connect to '%s:%s'. Check host, port, and firewall.",
            settings.SMTP_HOST,
            settings.SMTP_PORT,
        )
        raise
    except smtplib.SMTPException:
        logger_instance.exception("An SMTP error occurred while sending the email.")
        raise
    except Exception:
        logger_instance.exception("An unexpected error occurred during email sending.")
        raise
