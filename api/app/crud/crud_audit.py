"""
app/crud/crud_audit.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.audit.repositories.audit_repository import AuditRepository, CRUDAudit

__all__ = ["AuditRepository", "CRUDAudit"]
