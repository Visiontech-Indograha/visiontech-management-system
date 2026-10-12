"""
app/modules/audit/services/audit_service.py

Layanan logika bisnis untuk modul audit kejadian sistem.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""
from app.services.audit_service import AuditService as BaseAuditService


class AuditService(BaseAuditService):
    """
    Layanan bisnis log audit.
    Mengelola pengambilan riwayat audit per organisasi dan pencatatan jejak sistem.
    """


__all__ = ["AuditService"]
