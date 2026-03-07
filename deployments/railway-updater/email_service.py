#!/usr/bin/env python3
"""
Email Service - Reusable email sending with AWS SES and SMTP fallback
Supports different recipients for different types of notifications
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Try to import boto3 for AWS SES
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


class EmailService:
    """Email service with AWS SES and SMTP fallback"""

    def __init__(self, default_from=None, default_to=None):
        """
        Initialize email service with configuration from environment

        Args:
            default_from: Default sender email (overrides env var)
            default_to: Default recipient email (overrides env var)
        """
        # Email configuration
        self.email_from = default_from or os.getenv("DEFAULT_FROM_EMAIL", "hello@sinclairpatterns.com")
        self.email_to = default_to or os.getenv("NOTIFICATION_EMAIL", "hello@sinclairpatterns.com")

        # AWS SES configuration
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_SES_REGION_NAME", "us-east-1")
        self.aws_endpoint = os.getenv("AWS_SES_REGION_ENDPOINT")

        # SMTP configuration (fallback)
        self.smtp_host = os.getenv("EMAIL_HOST", "smtp.zoho.com")
        self.smtp_port = int(os.getenv("EMAIL_PORT", "587"))
        self.smtp_user = os.getenv("EMAIL_HOST_USER")
        self.smtp_password = os.getenv("EMAIL_HOST_PASSWORD")
        self.smtp_use_tls = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"

        # Track which method works
        self.preferred_method = None

    def send(self, subject, body, to_email=None, from_email=None, html=False):
        """
        Send an email using AWS SES (preferred) or SMTP fallback

        Args:
            subject: Email subject line
            body: Email body content
            to_email: Recipient email (uses default if None)
            from_email: Sender email (uses default if None)
            html: If True, send as HTML email

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        to_email = to_email or self.email_to
        from_email = from_email or self.email_from

        # Try AWS SES first (HTTP API - works on Railway)
        if HAS_BOTO3 and self.aws_access_key and self.aws_secret_key:
            if self._send_via_ses(subject, body, to_email, from_email, html):
                return True

        # Fallback to SMTP (may not work on Railway due to port blocking)
        if self.smtp_user and self.smtp_password:
            if self._send_via_smtp(subject, body, to_email, from_email, html):
                return True

        return False

    def _send_via_ses(self, subject, body, to_email, from_email, html):
        """Send email via AWS SES HTTP API"""
        try:
            ses_kwargs = {
                'region_name': self.aws_region,
                'aws_access_key_id': self.aws_access_key,
                'aws_secret_access_key': self.aws_secret_key
            }

            # Add endpoint if specified (but skip SMTP endpoints)
            # AWS SES HTTP API endpoint format: https://email.REGION.amazonaws.com
            # Don't use email-smtp.* endpoints (those are for SMTP only)
            if self.aws_endpoint and 'email-smtp' not in self.aws_endpoint:
                # Ensure endpoint has https:// prefix
                endpoint = self.aws_endpoint
                if not endpoint.startswith('http'):
                    endpoint = f'https://{endpoint}'
                ses_kwargs['endpoint_url'] = endpoint

            ses_client = boto3.client('ses', **ses_kwargs)

            response = ses_client.send_email(
                Source=from_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {
                        'Html': {'Data': body} if html else {'Data': ''},
                        'Text': {'Data': body if not html else ''}
                    }
                }
            )

            print(f"✉️  Email sent via AWS SES to {to_email}: {subject}")
            print(f"   MessageId: {response['MessageId']}")
            self.preferred_method = 'ses'
            return True

        except ClientError as e:
            print(f"⚠️  AWS SES failed: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            print(f"⚠️  AWS SES error: {type(e).__name__}: {e}")
            return False

    def _send_via_smtp(self, subject, body, to_email, from_email, html):
        """Send email via SMTP (fallback)"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)

            if self.smtp_use_tls:
                server.starttls()

            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()

            print(f"✉️  Email sent via SMTP to {to_email}: {subject}")
            self.preferred_method = 'smtp'
            return True

        except Exception as e:
            print(f"⚠️  SMTP failed: {type(e).__name__}: {e}")
            return False

    def send_notification(self, subject, body, html=False):
        """Send a notification email to default recipient"""
        return self.send(subject, body, html=html)

    def send_report(self, subject, body, to_email="ss@muffinsky.com", html=False):
        """
        Send a report email to specified recipient

        Args:
            subject: Report subject
            body: Report content
            to_email: Report recipient (defaults to ss@muffinsky.com)
            html: If True, send as HTML
        """
        return self.send(subject, body, to_email=to_email, html=html)
