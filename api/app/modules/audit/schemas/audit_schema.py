"""
app/modules/audit/schemas/audit_schema.py

Skema validasi permintaan dan respons log audit kejadian sistem.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""
from app.schemas.audit import AuditEventListResponse, AuditEventResponse

__all__ = ["AuditEventListResponse", "AuditEventResponse"]
