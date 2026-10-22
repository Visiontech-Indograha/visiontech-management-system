"""
app/modules/image_requirements/dependencies.py

Perakitan service modul image_requirements untuk FastAPI `Depends`.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.image_requirements.services.image_requirement_service import ImageRequirementService


def get_image_requirement_service(db: AsyncSession = Depends(get_db_with_user)) -> ImageRequirementService:
    return ImageRequirementService(db)
