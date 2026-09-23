from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import uuid

async def check_is_plan_leader(db: AsyncSession, plan_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    query = text("SELECT vms.is_plan_leader(:plan_id, :user_id)")
    result = await db.execute(query, {"plan_id": plan_id, "user_id": user_id})
    is_leader = result.scalar()
    if not is_leader:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not the active leader for this plan"
        )
    return True

async def check_is_plan_member(db: AsyncSession, plan_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    query = text("SELECT vms.is_plan_member(:plan_id, :user_id)")
    result = await db.execute(query, {"plan_id": plan_id, "user_id": user_id})
    is_member = result.scalar()
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not an active member for this plan"
        )
    return True
