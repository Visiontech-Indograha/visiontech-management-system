"""
Modul integrasi Discord untuk VMS.

Menyediakan utilitas untuk memformat dan mengirim notifikasi atau peringatan (alerts)
sistem ke saluran Discord melalui webhook, dilengkapi dengan penyaringan (sanitization)
data sensitif (seperti email, NIK, dan token).
"""
import logging
import re

import httpx

logger = logging.getLogger(__name__)

def sanitize_for_discord(text: str) -> str:
    """
    Menyaring data sensitif dari pesan sebelum dikirim ke Discord.
    - Menghapus NIK (16 digit angka)
    - Menyembunyikan alamat email
    - Menyembunyikan nomor telepon
    - Menyembunyikan token seperti JWT
    """
    if not isinstance(text, str):
        return text
    
    # Sembunyikan NIK (16 digit angka)
    text = re.sub(r'\b\d{16}\b', '[NIK_MASKED]', text)
    
    # Sembunyikan alamat Email
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', '[EMAIL_MASKED]', text)
    
    # Sembunyikan nomor telepon (pola sederhana +62 atau awalan 08)
    text = re.sub(r'\+62\d{9,13}', '[PHONE_MASKED]', text)
    text = re.sub(r'\b08\d{8,11}\b', '[PHONE_MASKED]', text)
    
    # Sembunyikan token/JWT
    text = re.sub(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}', '[JWT_MASKED]', text)
    
    return text

async def send_discord_alert(webhook_url: str, message: str, level: str = "error") -> None:
    """
    Mengirim pesan peringatan ke webhook Discord secara asinkron.
    Jika URL webhook kosong, peringatan hanya akan dicatat di log aplikasi.
    """
    if not webhook_url:
        logger.warning("URL webhook Discord tidak dikonfigurasi.")
        return

    # Saring pesan untuk menghindari kebocoran data
    sanitized_message = sanitize_for_discord(message)
    
    # Tentukan ikon awalan berdasarkan tingkat keparahan
    prefix = "🔴" if level == "error" else "⚠️" if level == "warning" else "ℹ️"
    
    # Format payload sesuai spesifikasi Discord
    payload = {
        "content": f"{prefix} **System Alert**\n```\n{sanitized_message}\n```"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Kirim request POST ke webhook
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
        except Exception as e:
            # Kegagalan kirim tidak boleh merusak alur aplikasi (fail-safe)
            logger.error(f"Gagal mengirim peringatan Discord: {e}")

