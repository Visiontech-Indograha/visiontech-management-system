"""
Router API v1 (docs/12 §1): menggabungkan semua endpoint. `main.py` memasangnya di bawah `/api/v1`.
Urutan include disalin apa adanya dari `main.py` lama (R-28 M2) — urutan memengaruhi OpenAPI.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.accounts import router as accounts_router
from app.api.v1.endpoints.assets import plan_assets_router
from app.api.v1.endpoints.assets import router as assets_router
from app.api.v1.endpoints.attendance import router as attendance_router
from app.api.v1.endpoints.attendance_cron import router as attendance_cron_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.employees import router as employees_router
from app.api.v1.endpoints.expiry import router as expiry_router
from app.api.v1.endpoints.files import router as files_router
from app.api.v1.endpoints.hse import days_router as daily_report_router
from app.api.v1.endpoints.hse import router as hse_router
from app.api.v1.endpoints.monitoring import router as monitoring_router
from app.api.v1.endpoints.overtime import overtime_router
from app.api.v1.endpoints.overtime import recaps_router as overtime_recaps_router
from app.api.v1.endpoints.signatures import plan_documents_router
from app.api.v1.endpoints.signatures import router as signatures_router
from app.api.v1.endpoints.sites import router as sites_router
from app.api.v1.endpoints.sync import router as sync_router
from app.api.v1.endpoints.units import router as units_router
from app.api.v1.endpoints.weekly_reports import router as weekly_reports_router
from app.api.v1.endpoints.work_plan_attachments import router as plan_attachments_router
from app.api.v1.endpoints.work_plan_changes import plan_router as plan_changes_router
from app.api.v1.endpoints.work_plan_changes import router as changes_router
from app.api.v1.endpoints.work_plan_days import router as plan_days_router
from app.api.v1.endpoints.work_plan_location import router as plan_location_router
from app.api.v1.endpoints.work_plan_members import router as plan_members_router
from app.api.v1.endpoints.work_plan_transitions import router as transitions_router
from app.api.v1.endpoints.work_plans import router as plans_router

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
api_router.include_router(attendance_cron_router)
api_router.include_router(hse_router)
api_router.include_router(daily_report_router)
api_router.include_router(assets_router)
api_router.include_router(plan_assets_router)
api_router.include_router(overtime_router)
api_router.include_router(overtime_recaps_router)
