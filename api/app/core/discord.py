import logging
import re

import httpx

logger = logging.getLogger(__name__)

def sanitize_for_discord(text: str) -> str:
    """
    Sanitize sensitive data from messages before sending to Discord.
    - Removes NIKs (16 digits)
    - Replaces emails
    - Removes phone numbers
    - Removes tokens, JWTs, etc.
    """
    if not isinstance(text, str):
        return text
    
    # Hide NIK (16 digit numbers)
    text = re.sub(r'\b\d{16}\b', '[NIK_MASKED]', text)
    
    # Hide Emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', '[EMAIL_MASKED]', text)
    
    # Hide phone numbers (simplistic)
    text = re.sub(r'\+62\d{9,13}', '[PHONE_MASKED]', text)
    text = re.sub(r'\b08\d{8,11}\b', '[PHONE_MASKED]', text)
    
    # Hide tokens/JWTs
    text = re.sub(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}', '[JWT_MASKED]', text)
    
    return text

async def send_discord_alert(webhook_url: str, message: str, level: str = "error"):
    """
    Send an alert to Discord webhook.
    """
    if not webhook_url:
        logger.warning("Discord webhook URL not configured.")
        return

    sanitized_message = sanitize_for_discord(message)
    
    prefix = "🔴" if level == "error" else "⚠️" if level == "warning" else "ℹ️"
    
    payload = {
        "content": f"{prefix} **System Alert**\n```\n{sanitized_message}\n```"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
