"""
Pinplot SendGrid connectivity test.
Run on the server from ~/pinplot/gps-tracker:

    docker exec pinplot_backend python test_sendgrid_pinplot.py

Or locally if sendgrid is installed:
    python test_sendgrid_pinplot.py
"""
import os
import sys

# Allow running from gps-tracker dir without installing the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

TO_EMAIL   = "carlmukoyi@gmail.com"
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@pinplot.me")
API_KEY    = os.getenv("SENDGRID_API_KEY", "")

if not API_KEY:
    print("❌  SENDGRID_API_KEY not set in environment.")
    print("    Run inside the container:  docker exec pinplot_backend python test_sendgrid_pinplot.py")
    sys.exit(1)

print(f"📧  From      : {FROM_EMAIL}")
print(f"📧  To        : {TO_EMAIL}")
print(f"🔑  Key prefix: {API_KEY[:20]}…")
print()

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, TrackingSettings, ClickTracking
except ImportError:
    print("❌  sendgrid package not installed.")
    sys.exit(1)

message = Mail(
    from_email=FROM_EMAIL,
    to_emails=TO_EMAIL,
    subject="[Pinplot] SendGrid test email",
    plain_text_content="This is a test email from noreply@pinplot.me via SendGrid. If you received this, email sending is working correctly.",
    html_content=(
        "<div style='font-family:Arial,sans-serif;padding:20px'>"
        "<h2 style='color:#173C64'>✅ Pinplot Email Test</h2>"
        "<p>This is a test email sent from <strong>noreply@pinplot.me</strong> via SendGrid.</p>"
        "<p>If you received this, email sending is working correctly for Pinplot.</p>"
        "</div>"
    )
)

# Disable click tracking
ts = TrackingSettings()
ts.click_tracking = ClickTracking(enable=False, enable_text=False)
message.tracking_settings = ts

try:
    sg = SendGridAPIClient(API_KEY)
    response = sg.send(message)
    print(f"✅  Sent! Status: {response.status_code}")
    print(f"    Check {TO_EMAIL} inbox.")
except Exception as e:
    print(f"❌  Failed: {e}")
    if hasattr(e, 'body'):
        print(f"    Body: {e.body}")
    if hasattr(e, 'status_code'):
        print(f"    Status: {e.status_code}")
    sys.exit(1)
