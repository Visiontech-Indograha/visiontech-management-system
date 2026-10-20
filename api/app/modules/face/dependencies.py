"""
app/modules/face/dependencies.py

Perakitan service modul face untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.face.repositories.face_repository import CRUDFace
from app.modules.face.services.face_embed_client import FaceEmbedClient
from app.modules.face.services.face_service import FaceService


def get_face_embed_client() -> FaceEmbedClient:
    """Klien face-service. Dependency tersendiri agar uji dapat menggantinya dengan tiruan."""
    return FaceEmbedClient()


def get_face_service(db: AsyncSession = Depends(get_db_with_user),
                     client: FaceEmbedClient = Depends(get_face_embed_client)) -> FaceService:
    return FaceService(CRUDFace(db), client)
