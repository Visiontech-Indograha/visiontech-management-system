import uuid

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_is_plan_leader(db: AsyncSession, plan_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    query = text(
        """
        SELECT EXISTS (
            SELECT 1 FROM work_plan_weekly wp
            JOIN team t ON t.team_id = wp.team_id
            JOIN users u ON u.employee_id = t.leader_employee_id
            WHERE wp.weekly_plan_id = :plan_id AND u.user_id = :user_id
            UNION
            SELECT 1 FROM users u
            WHERE u.user_id = :user_id AND u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'PROJECT_MANAGER')
        )
        """
    )
    result = await db.execute(query, {"plan_id": plan_id, "user_id": user_id})
    is_leader = result.scalar()
    if not is_leader:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not the active leader for this plan",
        )
    return True


async def check_is_plan_member(db: AsyncSession, plan_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    query = text(
        """
        SELECT EXISTS (
            SELECT 1 FROM work_plan_weekly wp
            JOIN member m ON m.team_id = wp.team_id AND m.is_active = TRUE AND m.delete_at IS NULL
            JOIN users u ON u.employee_id = m.employee_id
            WHERE wp.weekly_plan_id = :plan_id AND u.user_id = :user_id
            UNION
            SELECT 1 FROM work_plan_weekly wp
            JOIN team t ON t.team_id = wp.team_id
            JOIN users u ON u.employee_id = t.leader_employee_id
            WHERE wp.weekly_plan_id = :plan_id AND u.user_id = :user_id
            UNION
            SELECT 1 FROM users u
            WHERE u.user_id = :user_id AND u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'PROJECT_MANAGER')
        )
        """
    )
    result = await db.execute(query, {"plan_id": plan_id, "user_id": user_id})
    is_member = result.scalar()
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not an active member for this plan",
        )
    return True
