import logging
from typing import Optional
from app.core.discord import send_to_discord

logger = logging.getLogger(__name__)

async def send_security_alert(title: str, description: str, details: Optional[dict] = None):
    """
    Mengirim peringatan keamanan ke Discord webhook #vms-alerts
    """
    message = f"**[SECURITY ALERT] {title}**\n{description}"
    if details:
        message += "\n```json\n" + str(details) + "\n```"
        
    logger.warning(f"SECURITY ALERT: {title} - {description} - {details}")
    try:
        await send_to_discord(message)
    except Exception as e:
        logger.error(f"Gagal mengirim alert ke Discord: {e}")
