#!/usr/bin/env python3
"""
Test AWS SES email sending locally
"""

import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# Get AWS credentials from environment
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SES_REGION_NAME = os.getenv("AWS_SES_REGION_NAME", "us-east-1")
AWS_SES_REGION_ENDPOINT = os.getenv("AWS_SES_REGION_ENDPOINT")

EMAIL_FROM = os.getenv("DEFAULT_FROM_EMAIL", "hello@sinclairpatterns.com")
EMAIL_TO = os.getenv("NOTIFICATION_EMAIL", "hello@sinclairpatterns.com")

print("="*70)
print("AWS SES EMAIL TEST")
print("="*70)
print(f"\nConfiguration:")
print(f"  AWS_ACCESS_KEY_ID: {AWS_ACCESS_KEY_ID[:10]}..." if AWS_ACCESS_KEY_ID else "  AWS_ACCESS_KEY_ID: NOT SET")
print(f"  AWS_SECRET_ACCESS_KEY: {'*' * 20}")
print(f"  AWS_SES_REGION_NAME: {AWS_SES_REGION_NAME}")
print(f"  AWS_SES_REGION_ENDPOINT: {AWS_SES_REGION_ENDPOINT}")
print(f"  EMAIL_FROM: {EMAIL_FROM}")
print(f"  EMAIL_TO: {EMAIL_TO}")
print()

if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    print("❌ AWS credentials not set!")
    print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
    exit(1)

try:
    print("Creating SES client...")

    ses_kwargs = {
        'region_name': AWS_SES_REGION_NAME,
        'aws_access_key_id': AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': AWS_SECRET_ACCESS_KEY
    }

    # Add endpoint if specified (but skip SMTP endpoints)
    # AWS SES HTTP API endpoint format: https://email.REGION.amazonaws.com
    # Don't use email-smtp.* endpoints (those are for SMTP only)
    if AWS_SES_REGION_ENDPOINT:
        if 'email-smtp' in AWS_SES_REGION_ENDPOINT:
            print(f"  ⚠️  Skipping SMTP endpoint (not for HTTP API): {AWS_SES_REGION_ENDPOINT}")
            print(f"  Using default AWS SES endpoint for region: {AWS_SES_REGION_NAME}")
        else:
            # Ensure endpoint has https:// prefix
            endpoint = AWS_SES_REGION_ENDPOINT
            if not endpoint.startswith('http'):
                endpoint = f'https://{endpoint}'
            print(f"  Using custom endpoint: {endpoint}")
            ses_kwargs['endpoint_url'] = endpoint

    ses_client = boto3.client('ses', **ses_kwargs)
    print("✓ SES client created")

    # Test: Get sending quota
    print("\nTesting SES connection...")
    quota = ses_client.get_send_quota()
    print("✓ Connection successful!")
    print(f"  Max 24 Hour Send: {quota['Max24HourSend']:.0f}")
    print(f"  Sent Last 24 Hours: {quota['SentLast24Hours']:.0f}")
    print(f"  Max Send Rate: {quota['MaxSendRate']:.0f}/sec")

    # Test: List verified emails
    print("\nChecking verified email addresses...")
    identities = ses_client.list_verified_email_addresses()
    verified = identities.get('VerifiedEmailAddresses', [])

    if verified:
        print(f"✓ Found {len(verified)} verified email(s):")
        for email in verified:
            print(f"  - {email}")
    else:
        print("⚠️  No verified email addresses found!")
        print("   You need to verify at least the FROM email in AWS SES console")

    # Check if FROM email is verified
    if EMAIL_FROM not in verified:
        print(f"\n⚠️  WARNING: {EMAIL_FROM} is NOT verified!")
        print("   Emails will fail unless you verify this address in AWS SES")
        print("   Go to: https://console.aws.amazon.com/ses/")

    # Send test email
    print(f"\n{'='*70}")
    print(f"Sending test email from {EMAIL_FROM} to {EMAIL_TO}...")

    response = ses_client.send_email(
        Source=EMAIL_FROM,
        Destination={'ToAddresses': [EMAIL_TO]},
        Message={
            'Subject': {'Data': 'Test Email from Shopify Updater'},
            'Body': {
                'Text': {
                    'Data': '''This is a test email from the Shopify Orders Updater.

If you received this, AWS SES is working correctly!

Configuration:
- Region: {region}
- Endpoint: {endpoint}

Sent from local test script.
'''.format(region=AWS_SES_REGION_NAME, endpoint=AWS_SES_REGION_ENDPOINT or 'Default')
                }
            }
        }
    )

    print(f"✅ Email sent successfully!")
    print(f"   Message ID: {response['MessageId']}")
    print(f"   Check {EMAIL_TO} for the test email")

except ClientError as e:
    print(f"\n❌ AWS SES Error:")
    print(f"   Code: {e.response['Error']['Code']}")
    print(f"   Message: {e.response['Error']['Message']}")

    if 'InvalidParameterValue' in str(e):
        print("\n💡 Tip: Check that EMAIL_FROM is verified in AWS SES")
    elif 'InvalidClientTokenId' in str(e):
        print("\n💡 Tip: Check your AWS_ACCESS_KEY_ID")
    elif 'SignatureDoesNotMatch' in str(e):
        print("\n💡 Tip: Check your AWS_SECRET_ACCESS_KEY")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
