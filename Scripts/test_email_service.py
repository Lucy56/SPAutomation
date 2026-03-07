#!/usr/bin/env python3
"""
Test the new EmailService class
"""

import sys
import os

# Add the railway-updater directory to path so we can import email_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../deployments/railway-updater'))

from dotenv import load_dotenv
from email_service import EmailService

load_dotenv()

print("="*70)
print("EMAIL SERVICE TEST")
print("="*70)

# Initialize email service
email_service = EmailService()

print(f"\nConfiguration:")
print(f"  Default FROM: {email_service.email_from}")
print(f"  Default TO: {email_service.email_to}")
print(f"  AWS Region: {email_service.aws_region}")
print(f"  AWS Access Key: {email_service.aws_access_key[:10]}..." if email_service.aws_access_key else "  AWS Access Key: NOT SET")

# Test 1: Send notification to default recipient
print("\n" + "="*70)
print("TEST 1: Send notification to default recipient")
print("="*70)
result = email_service.send_notification(
    subject="Test Notification from EmailService",
    body="""This is a test notification sent via the new EmailService class.

This email should go to: hello@sinclairpatterns.com

Sent from test_email_service.py"""
)

if result:
    print("✅ Notification sent successfully!")
else:
    print("❌ Notification failed!")

# Test 2: Send report to ss@muffinsky.com
print("\n" + "="*70)
print("TEST 2: Send report to ss@muffinsky.com")
print("="*70)
result = email_service.send_report(
    subject="Test Report from EmailService",
    body="""This is a test report sent via the new EmailService class.

This email should go to: ss@muffinsky.com

Key metrics:
- Orders synced: 261,822
- Time taken: 45 minutes
- Status: Success

Sent from test_email_service.py"""
)

if result:
    print("✅ Report sent successfully!")
else:
    print("❌ Report failed!")

# Test 3: Send to custom recipient
print("\n" + "="*70)
print("TEST 3: Send to custom recipient")
print("="*70)
custom_email = input("Enter email to test (or press Enter to skip): ").strip()

if custom_email:
    result = email_service.send(
        subject="Test Custom Recipient from EmailService",
        body=f"""This is a test email sent to a custom recipient.

Sent to: {custom_email}

Sent from test_email_service.py""",
        to_email=custom_email
    )

    if result:
        print(f"✅ Email sent successfully to {custom_email}!")
    else:
        print(f"❌ Email failed to {custom_email}!")
else:
    print("Skipped custom recipient test")

print("\n" + "="*70)
print("TESTS COMPLETE")
print("="*70)
print(f"\nPreferred method: {email_service.preferred_method or 'none worked'}")
print("\nCheck your inboxes:")
print("  - hello@sinclairpatterns.com (notification)")
print("  - ss@muffinsky.com (report)")
if custom_email:
    print(f"  - {custom_email} (custom)")
