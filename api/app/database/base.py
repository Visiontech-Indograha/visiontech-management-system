"""
Fasilitas metadata dasar dan deklarasi model database ORM.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §3 & §5.6.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Kelas dasar deklaratif untuk semua model database ORM SQLAlchemy.
    """
