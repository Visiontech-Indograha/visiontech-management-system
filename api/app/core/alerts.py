import logging

from app.core.config import settings
from app.core.discord import send_discord_alert

logger = logging.getLogger(__name__)


async def send_security_alert(title: str, description: str, details: dict[str, object] | None = None) -> None:
    """
    Mengirim peringatan keamanan ke Discord #vms-alerts (dok 17).
    Pesan disaring `sanitize_for_discord`; `send_discord_alert` menelan galat kirim sendiri,
    jadi peringatan tidak pernah menggagalkan permintaan pengguna.
    """
    message = f"**[SECURITY ALERT] {title}**\n{description}"
    if details:
        message += "\n```json\n" + str(details) + "\n```"

    logger.warning(f"SECURITY ALERT: {title} - {description} - {details}")
    await send_discord_alert(settings.DISCORD_WEBHOOK_ALERTS, message, level="warning")
