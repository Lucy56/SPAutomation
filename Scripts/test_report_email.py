#!/usr/bin/env python3
"""
Test that reports go to ss@muffinsky.com
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../deployments/railway-updater'))

from dotenv import load_dotenv
from email_service import EmailService

load_dotenv()

print("="*70)
print("REPORT EMAIL TEST")
print("="*70)

email_service = EmailService()

print(f"\nEmail service configuration:")
print(f"  Default recipient (notifications): {email_service.email_to}")
print(f"  Report recipient: ss@muffinsky.com")

# Test that send_report goes to ss@muffinsky.com
print("\n" + "="*70)
print("Sending test report to ss@muffinsky.com...")
print("="*70)

result = email_service.send_report(
    subject='Test Report - Should go to ss@muffinsky.com',
    body='''This email should arrive at ss@muffinsky.com

This is a test to verify that sync reports go to the correct email address.

Expected recipient: ss@muffinsky.com
Should NOT go to: hello@sinclairpatterns.com

If you received this at ss@muffinsky.com, the routing is working correctly!
'''
)

if result:
    print('✅ Email sent successfully')
    print('   Check ss@muffinsky.com inbox')
else:
    print('❌ Failed to send email')

print("\n" + "="*70)
