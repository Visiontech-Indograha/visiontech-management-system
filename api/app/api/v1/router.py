"""
Router API v1 (docs/12 §1): menggabungkan semua endpoint. `main.py` memasangnya di bawah `/api/v1`.
Urutan include disalin apa adanya dari `main.py` lama (R-28 M2) — urutan memengaruhi OpenAPI.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.face import router as face_router
from app.modules.accounts.routes import router as accounts_router
from app.modules.assets.routes import assets_router, plan_assets_router
from app.modules.attendance.routes import attendance_cron_router, attendance_router
from app.modules.audit.routes import audit_router
from app.modules.auth.routes import router as auth_router
from app.modules.documents.routes import documents_router, expiry_router
from app.modules.employees.routes import router as employees_router
from app.modules.hse.routes import daily_report_router, hse_router
from app.modules.notifications.routes import notifications_router
from app.modules.overtime.routes import overtime_recaps_router, overtime_router
from app.modules.reports.routes import weekly_reports_router
from app.modules.signatures.routes import plan_documents_router, signatures_router
from app.modules.sites.routes import router as sites_router
from app.modules.system.routes import (
    app_releases_router,
    events_router,
    files_router,
    monitoring_router,
    sync_router,
)
from app.modules.units.routes import router as units_router
from app.modules.work_plans.routes import (
    changes_router,
    plan_amendments_router,
    plan_attachments_router,
    plan_changes_router,
    plan_days_router,
    plan_location_router,
    plan_members_router,
    plan_reports_router,
    plan_revisions_router,
    plans_router,
    transitions_router,
)
from app.modules.work_types.routes import router as work_types_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(files_router)
api_router.include_router(employees_router)
api_router.include_router(documents_router)
api_router.include_router(expiry_router)
api_router.include_router(plans_router)
api_router.include_router(plan_members_router)
api_router.include_router(transitions_router)
api_router.include_router(plan_changes_router)
api_router.include_router(changes_router)
api_router.include_router(sites_router)
api_router.include_router(units_router)
api_router.include_router(accounts_router)
api_router.include_router(sync_router)
api_router.include_router(plan_location_router)
api_router.include_router(weekly_reports_router)
api_router.include_router(monitoring_router)
api_router.include_router(plan_attachments_router)
api_router.include_router(plan_days_router)
api_router.include_router(plan_documents_router)
api_router.include_router(signatures_router)
api_router.include_router(attendance_router)
api_router.include_router(face_router)
api_router.include_router(attendance_cron_router)
api_router.include_router(hse_router)
api_router.include_router(daily_report_router)
api_router.include_router(assets_router)
api_router.include_router(plan_assets_router)
api_router.include_router(overtime_router)
api_router.include_router(overtime_recaps_router)
api_router.include_router(notifications_router)
api_router.include_router(plan_reports_router)
api_router.include_router(plan_amendments_router)
api_router.include_router(plan_revisions_router)
api_router.include_router(events_router)
api_router.include_router(work_types_router)
api_router.include_router(app_releases_router)
