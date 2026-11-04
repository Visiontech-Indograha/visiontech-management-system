"""
app/modules/work_orders/dependencies.py
Perakitan service modul work_orders untuk FastAPI Depends.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.modules.work_orders.services.work_order_service import WorkOrderService


def get_work_order_service(db: AsyncSession = Depends(get_db_with_user)) -> WorkOrderService:
    return WorkOrderService(db, WorkOrderRepository(db))
