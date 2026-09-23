from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
from app.api.deps import get_db_with_user
from app.core.discord import send_discord_alert
from app.core.config import settings

router = APIRouter(prefix="/cron/attendance", tags=["Attendance Cron"])

@router.post("/alert-missing")
async def alert_missing_checkin(db: AsyncSession = Depends(get_db_with_user)):
    """P4-9: Peringatan bisnis -> Discord: tidak ada absensi masuk sampai 09.00 WIB"""
    if datetime.now().hour != 9:
        return {"status": "skipped", "message": "Bukan jam 09:00"}
        
    query = text("""
        SELECT e.full_name, e.employee_no 
        FROM vms.employee e
        WHERE e.is_active = true 
          AND e.id NOT IN (
              SELECT employee_id FROM vms.attendance 
              WHERE work_date = CURRENT_DATE
          )
    """)
    rows = (await db.execute(query)).fetchall()
    
    if rows:
        names = ", ".join([f"{r.full_name} ({r.employee_no})" for r in rows])
        await send_discord_alert(
            webhook_url=settings.DISCORD_WEBHOOK_URL,
            message=f"Terdapat {len(rows)} karyawan aktif yang belum check-in hari ini:\n\n{names}",
            level="warning"
        )
    return {"missing_count": len(rows)}

@router.post("/alert-needs-review")
async def alert_needs_review_spike(db: AsyncSession = Depends(get_db_with_user)):
    """P4-9: Peringatan bisnis -> Discord: lonjakan NEEDS_REVIEW"""
    query = text("SELECT count(*) FROM vms.attendance WHERE status = 'NEEDS_REVIEW'")
    count = (await db.execute(query)).scalar()
    
    if count > 10:  # Threshold lonjakan
        await send_discord_alert(
            webhook_url=settings.DISCORD_WEBHOOK_URL,
            message=f"Terdapat {count} absensi yang menunggu review dari Finance/HRD. Mohon segera diproses.",
            level="error"
        )
    return {"needs_review_count": count}
