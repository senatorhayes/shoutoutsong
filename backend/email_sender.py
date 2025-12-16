# email_sender.py
import os
import requests
from pathlib import Path

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = "ShoutoutSong <songs@shoutoutsong.com>"  # You'll verify this domain in Resend

# Load email template
TEMPLATE_PATH = Path(__file__).parent / "email_template.html"
with open(TEMPLATE_PATH, 'r') as f:
    EMAIL_TEMPLATE = f.read()


def send_song_email(
    to_email: str,
    recipient_name: str,
    subject: str,
    download_url: str,
    share_url: str
):
    """
    Send the song delivery email using Resend.
    
    Args:
        to_email: Recipient email address
        recipient_name: Name of person song is about
        subject: What the song is about
        download_url: Direct download link for MP3
        share_url: Shareable link
    
    Returns:
        dict: Response from Resend API
    """
    
    if not RESEND_API_KEY:
        print("⚠️ RESEND_API_KEY not configured - email not sent")
        return None
    
    # Fill in template
    html_content = EMAIL_TEMPLATE.replace("{{recipient_name}}", recipient_name)
    html_content = html_content.replace("{{subject}}", subject)
    html_content = html_content.replace("{{download_url}}", download_url)
    html_content = html_content.replace("{{share_url}}", share_url)
    
    # Plain text fallback
    text_content = f"""
Your Shoutout Song is Ready! 🎉

A song about {recipient_name} and their love for {subject}

Download: {download_url}
Share: {share_url}

Make another: https://shoutoutsong.com

---
© 2025 ShoutoutSong
    """.strip()
    
    # Send via Resend API
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": FROM_EMAIL,
                "to": [to_email],
                "subject": f"🎵 Your song about {recipient_name} is ready!",
                "html": html_content,
                "text": text_content
            }
        )
        
        if response.status_code == 200:
            print(f"✅ Email sent to {to_email}")
            return response.json()
        else:
            print(f"❌ Email failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Email error: {e}")
        return None
