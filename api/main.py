"""
api/main.py
Entrypoint alias untuk uvicorn dari root direktori api.
Mengimpor instance aplikasi FastAPI dari app.main.
"""
from app.main import app

# Alias untuk fleksibilitas pemanggilan uvicorn
main = app

__all__ = ["app", "main"]
