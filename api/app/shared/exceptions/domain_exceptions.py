"""
app/shared/exceptions/domain_exceptions.py

Exception domain terstandarisasi untuk kegagalan bisnis.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3 & §8.
"""
from app.core.errors import AppError, trigger_rule_error

__all__ = [
    "AppError",
    "trigger_rule_error",
]

