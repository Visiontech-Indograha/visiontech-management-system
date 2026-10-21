"""
Router API v1 (docs/12 §1): menggabungkan semua endpoint. `main.py` memasangnya di bawah `/api/v1`.
Urutan include memengaruhi OpenAPI. Alur SK V1 dipensiunkan pada Milestone 5 (daily-first).
"""
from fastapi import APIRouter

from app.modules.accounts.routes import router as accounts_router
from app.modules.assets.routes import assets_router, plan_assets_router
from app.modules.attendance.routes import attendance_cron_router, attendance_router
from app.modules.audit.routes import audit_router
from app.modules.auth.routes import router as auth_router
from app.modules.clients.routes import router as clients_router
from app.modules.divisions.routes import router as divisions_router
from app.modules.documents.routes import documents_router, expiry_router
from app.modules.employees.routes import router as employees_router
from app.modules.exports.routes import router as exports_router
from app.modules.face.routes import router as face_router
from app.modules.image_requirements.routes import router as image_requirements_router
from app.modules.job_positions.routes import router as job_positions_router
from app.modules.mess.routes import router as mess_router
from app.modules.notifications.routes import notifications_router
from app.modules.offboarding.routes import router as offboarding_router
from app.modules.offices.routes import router as offices_router
from app.modules.overtime.routes import overtime_recaps_router, overtime_router
from app.modules.projects.routes import router as projects_router
from app.modules.system.routes import (
    app_releases_router,
    events_router,
    files_router,
    media_router,
    monitoring_router,
    sync_router,
)
from app.modules.system_backup.routes import router as backup_router
from app.modules.teams.routes import router as teams_router
from app.modules.work_completion.routes import router as work_completion_router
from app.modules.work_completion.routes import verify_router
from app.modules.work_plans.routes import daily_plans_router, plan_items_router
from app.modules.work_types.routes import router as work_types_router

api_router = APIRouter()

api_router.include_router(clients_router)
api_router.include_router(projects_router)
api_router.include_router(job_positions_router)
api_router.include_router(daily_plans_router)
api_router.include_router(plan_items_router)
api_router.include_router(work_completion_router)
api_router.include_router(exports_router)
api_router.include_router(verify_router)
api_router.include_router(teams_router)
api_router.include_router(mess_router)
api_router.include_router(offboarding_router)
api_router.include_router(image_requirements_router)
api_router.include_router(backup_router)

api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(files_router)
api_router.include_router(media_router)
api_router.include_router(employees_router)
api_router.include_router(documents_router)
api_router.include_router(expiry_router)

api_router.include_router(offices_router)
api_router.include_router(divisions_router)
api_router.include_router(accounts_router)
api_router.include_router(sync_router)
api_router.include_router(monitoring_router)
api_router.include_router(attendance_router)
api_router.include_router(face_router)
api_router.include_router(attendance_cron_router)
api_router.include_router(assets_router)
api_router.include_router(plan_assets_router)
api_router.include_router(overtime_router)
api_router.include_router(overtime_recaps_router)
api_router.include_router(notifications_router)
api_router.include_router(events_router)
api_router.include_router(work_types_router)
api_router.include_router(app_releases_router)
