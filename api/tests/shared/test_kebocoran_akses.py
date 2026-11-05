"""
Kebocoran akses (audit 2026-11): perilaku layanan dengan repository palsu — tanpa basis data.
Mencakup work order, karyawan (kolom sensitif & filter status), aset, berkas profil/aset, jadwal harian
untuk HR/GA, dan absensi (wajah) untuk PM.
"""
from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.errors import ForbiddenError, NotFoundError
from app.core.permissions import permissions_for_roles
from app.core.security import CurrentUser
from app.modules.assets.services.asset_service import AssetService
from app.modules.employees.services import employee_service as es
from app.modules.employees.services.employee_service import EmployeeService
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.shared.access import access_service as acc
from app.shared.access.access_service import DailyNeed, check_daily_access
from app.shared.access.daily_access_repository import DailyAccessRepository
from app.shared.access.file_access_repository import FileAccessRepository


@pytest.fixture
def anyio_backend() -> str:
    # Tes ini mandiri (tanpa conftest DB); uji async dijalankan lewat plugin anyio.
    return "asyncio"


def _user(*roles: str, employee_id: str | None = "11111111-1111-1111-1111-111111111111") -> CurrentUser:
    roles_list = list(roles) or ["EMPLOYEE"]
    return CurrentUser(
        user_id=str(uuid.uuid4()), organization_id="o", email="e@uji", role=roles_list[0], roles=roles_list,
        session_id="s", permissions=permissions_for_roles(roles_list), employee_id=employee_id,
    )


def _row(**fields: Any) -> SimpleNamespace:
    return SimpleNamespace(_mapping=fields, **fields)


# ── Work order (poin 1) ─────────────────────────────────────────────────────────

class _FakeWORepo:
    def __init__(self, detail: Any = None) -> None:
        self.detail = detail
        self.list_viewers: list[Any] = []
        self.get_viewers: list[Any] = []

    async def list_work_orders(self, **kwargs: Any) -> list[Any]:
        self.list_viewers.append(kwargs.get("viewer"))
        return []

    async def get_work_order(self, work_order_id: Any, viewer: Any = None) -> Any:
        self.get_viewers.append(viewer)
        return self.detail


@pytest.mark.anyio
async def test_work_order_list_passes_viewer_scope_except_for_full_scope_roles():
    repo = _FakeWORepo()
    svc = WorkOrderService(db=None, repo=repo)  # type: ignore[arg-type]
    await svc.list_work_orders(_user("PROJECT_MANAGER"))
    await svc.list_work_orders(_user("EMPLOYEE"))
    await svc.list_work_orders(_user("OPERATIONAL_MANAGER"))
    pm_scope, employee_scope, full = repo.list_viewers
    assert pm_scope["pm"] is True and pm_scope["viewer_emp"] == "11111111-1111-1111-1111-111111111111"
    assert employee_scope["pm"] is False
    assert full is None


@pytest.mark.anyio
async def test_work_order_detail_outside_scope_is_not_found():
    svc = WorkOrderService(db=None, repo=_FakeWORepo(detail=None))  # type: ignore[arg-type]
    with pytest.raises(NotFoundError):
        await svc.get_work_order(uuid.uuid4(), _user("EMPLOYEE"))


@pytest.mark.anyio
async def test_work_order_detail_for_full_scope_role_is_unrestricted():
    repo = _FakeWORepo(detail=None)
    svc = WorkOrderService(db=None, repo=repo)  # type: ignore[arg-type]
    with pytest.raises(NotFoundError):  # tidak ditemukan tetap 404, tetapi tanpa pembatasan cakupan
        await svc.get_work_order(uuid.uuid4(), _user("SUPER_ADMIN"))
    assert repo.get_viewers == [None]


# ── Karyawan (poin 3) ───────────────────────────────────────────────────────────

class _FakeEmployeeRepo:
    def __init__(self, row: Any = None) -> None:
        self.row = row
        self.db: Any = None   # flag peran-ganda mati: cakupan kantor tidak menyentuh DB
        self.page_scopes: list[Any] = []
        self.addresses_called = False

    async def page(self, limit: int, offset: int, scope: Any = None, **_: Any) -> list[Any]:
        self.page_scopes.append(scope)
        return [self.row] if self.row is not None else []

    async def count(self, scope: Any = None, **_: Any) -> int:
        return len(await self.page(0, 0, scope))

    async def get(self, employee_id: Any, scope: Any = None) -> Any:
        return self.row

    async def addresses(self, employee_id: Any) -> list[Any]:
        self.addresses_called = True
        return [_row(address_id="a", address_line="Jl. Uji", city="Kota", postal_code="12345")]


def _emp_row(*, sensitive_ok: bool) -> SimpleNamespace:
    return _row(
        employee_id="22222222-2222-2222-2222-222222222222", employee_no="E-1", full_name="Budi",
        office_id="33333333-3333-3333-3333-333333333333", office_name="Kantor", division_id=None,
        division_name=None, position_id=None, position_code=None, position_name=None, join_date="2024-01-01",
        pkwt_end_date="2026-12-31", phone_number="0812", photo_file_id=None, face_enrolled=False,
        offboarding_status="active", archived=False, user_id=None, email="b@uji", system_role="EMPLOYEE",
        account_active=True, city="Kota", create_at="2024-01-01T00:00:00+00:00",
        update_at="2024-01-01T00:00:00+00:00", sensitive_ok=sensitive_ok,
    )


def test_shape_blanks_sensitive_fields_and_drops_flag():
    shaped = es._shape(_emp_row(sensitive_ok=False)._mapping)
    assert "sensitive_ok" not in shaped
    for key in ("phone_number", "email", "city", "pkwt_end_date", "system_role", "account_active"):
        assert shaped[key] is None, key
    assert shaped["full_name"] == "Budi"          # data kerja tetap terlihat


def test_shape_keeps_sensitive_fields_for_authorised_viewer():
    shaped = es._shape(_emp_row(sensitive_ok=True)._mapping)
    assert shaped["phone_number"] == "0812" and shaped["system_role"] == "EMPLOYEE"


@pytest.mark.anyio
async def test_employee_detail_for_colleague_hides_contacts_and_addresses():
    repo = _FakeEmployeeRepo(row=_emp_row(sensitive_ok=False))
    svc = EmployeeService(repo)  # type: ignore[arg-type]
    detail = await svc.detail(uuid.uuid4(), _user("TEAM_LEADER"))
    assert detail["addresses"] == [] and detail["phone_number"] is None
    assert repo.addresses_called is False


@pytest.mark.anyio
async def test_employee_detail_outside_scope_is_not_found():
    svc = EmployeeService(_FakeEmployeeRepo(row=None))  # type: ignore[arg-type]
    with pytest.raises(NotFoundError):
        await svc.detail(uuid.uuid4(), _user("EMPLOYEE"))


@pytest.mark.anyio
async def test_employee_list_forbids_offboarding_status_filter_for_non_hr():
    svc = EmployeeService(_FakeEmployeeRepo())  # type: ignore[arg-type]
    with pytest.raises(ForbiddenError):
        await svc.list(page=1, size=20, status="offboarded", division_id=None, office_id=None,
                       position_id=None, q=None, user=_user("PROJECT_MANAGER"))


@pytest.mark.anyio
async def test_employee_list_passes_scope_to_repository():
    repo = _FakeEmployeeRepo(row=_emp_row(sensitive_ok=False))
    svc = EmployeeService(repo)  # type: ignore[arg-type]
    rows, total = await svc.list(page=1, size=20, status=None, division_id=None, office_id=None,
                                 position_id=None, q=None, user=_user("EMPLOYEE"))
    assert repo.page_scopes[0]["dir_all"] is False and repo.page_scopes[0]["sens_all"] is False
    assert rows[0]["phone_number"] is None and total == 1


# ── Aset (poin 4) ───────────────────────────────────────────────────────────────

class _FakeAssetRepo:
    def __init__(self) -> None:
        self.tool_viewers: list[Any] = []
        self.availability_viewers: list[Any] = []

    async def list_tools(self, office_id: Any, status: Any, viewer: Any = None, offices: Any = None) -> list[Any]:
        self.tool_viewers.append(viewer)
        return []

    async def availability(self, work_date: Any, viewer: Any = None, offices: Any = None) -> list[Any]:
        self.availability_viewers.append(viewer)
        return []

    async def team_names(self, team_ids: list[Any]) -> dict[str, str]:
        return {}


@pytest.mark.anyio
async def test_asset_list_and_availability_scoped_for_employee_unscoped_for_asset_manager():
    repo = _FakeAssetRepo()
    svc = AssetService(repo)  # type: ignore[arg-type]
    await svc.list_tools(None, None, _user("EMPLOYEE"))
    await svc.list_tools(None, None, _user("ASSET"))
    await svc.availability(date(2026, 11, 4), None, _user("EMPLOYEE"))
    employee_scope, manager_scope = repo.tool_viewers
    assert employee_scope is not None and employee_scope["pm"] is False
    assert manager_scope is None
    assert repo.availability_viewers[0] is not None


# ── Berkas (poin 5) ─────────────────────────────────────────────────────────────

def _file_row(**overrides: Any) -> SimpleNamespace:
    base: dict[str, Any] = {
        "id": uuid.uuid4(), "storage_key": "kantor/abc.png", "mime_type": "image/png", "file_name": "a.png",
        "uploaded_by": uuid.uuid4(), "public_in_org": False, "profile_photo": False, "profile_owner": None,
        "own_profile": False, "personal_document": False, "own_document": False, "selfie": False,
        "selfie_pm": False, "own_selfie": False, "asset_file": False, "daily_plan_ids": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _patch_links(monkeypatch: pytest.MonkeyPatch, row: Any) -> None:
    async def fake_links(self: Any, file_id: Any, employee_id: Any) -> Any:
        return row

    monkeypatch.setattr(FileAccessRepository, "links", fake_links)


@pytest.mark.anyio
async def test_profile_photo_of_other_division_is_hidden_from_employee(monkeypatch: pytest.MonkeyPatch):
    _patch_links(monkeypatch, _file_row(profile_photo=True, profile_owner=uuid.uuid4()))

    async def not_visible(db: Any, user: Any, employee_id: Any) -> bool:
        return False

    monkeypatch.setattr(acc, "employee_directory_visible", not_visible)
    with pytest.raises(NotFoundError):
        await acc.check_file_access(None, uuid.uuid4(), _user("EMPLOYEE"))  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_profile_photo_visible_when_employee_in_directory(monkeypatch: pytest.MonkeyPatch):
    row = _file_row(profile_photo=True, profile_owner=uuid.uuid4())
    _patch_links(monkeypatch, row)

    async def visible(db: Any, user: Any, employee_id: Any) -> bool:
        return True

    monkeypatch.setattr(acc, "employee_directory_visible", visible)
    assert await acc.check_file_access(None, uuid.uuid4(), _user("EMPLOYEE")) is row  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_asset_photo_is_not_public_to_every_logged_in_user(monkeypatch: pytest.MonkeyPatch):
    _patch_links(monkeypatch, _file_row(asset_file=True))

    async def not_visible(db: Any, key: Any, user: Any) -> bool:
        return False

    monkeypatch.setattr(acc, "asset_file_visible", not_visible)
    with pytest.raises(NotFoundError):
        await acc.check_file_access(None, uuid.uuid4(), _user("EMPLOYEE"))  # type: ignore[arg-type]


# ── Jadwal harian untuk HR/GA (poin 2) ──────────────────────────────────────────

def _plan_row(status: str = "APPROVED") -> SimpleNamespace:
    return SimpleNamespace(status=status, manages=False, is_leader=False, is_member=False,
                           daily_plan_id=uuid.uuid4(), division_id=None, team_id=None, pm_id=None, om_id=None,
                           leader_employee_id=None, work_date=None, kind="STANDARD")


@pytest.mark.anyio
async def test_hr_cannot_view_daily_plan_detail_but_can_use_logistics(monkeypatch: pytest.MonkeyPatch):
    async def standing(self: Any, daily_plan_id: Any, employee_id: Any) -> Any:
        return _plan_row()

    monkeypatch.setattr(DailyAccessRepository, "standing", standing)
    hr = _user("ADMIN_HR_GA")
    with pytest.raises(NotFoundError):
        await check_daily_access(None, uuid.uuid4(), hr, DailyNeed.VIEW)  # type: ignore[arg-type]
    access = await check_daily_access(None, uuid.uuid4(), hr, DailyNeed.LOGISTICS)  # type: ignore[arg-type]
    assert access.plan.status == "APPROVED"


@pytest.mark.anyio
async def test_super_admin_still_views_daily_plan(monkeypatch: pytest.MonkeyPatch):
    async def standing(self: Any, daily_plan_id: Any, employee_id: Any) -> Any:
        return _plan_row(status="DRAFT")

    monkeypatch.setattr(DailyAccessRepository, "standing", standing)
    access = await check_daily_access(None, uuid.uuid4(), _user("SUPER_ADMIN"), DailyNeed.VIEW)  # type: ignore[arg-type]
    assert access.manages is True


# ── Absensi: wajah untuk PM (poin 8) ────────────────────────────────────────────

def test_face_visibility_is_limited_to_own_division_not_project_reach():
    from app.modules.attendance.repositories.attendance_session_repository import _face_visible

    sql = _face_visible("a.employee_id")
    assert "dv.pm_id" in sql                       # PM divisi: bawahan di divisinya
    assert "rp_p.pm_id" not in sql and "project" not in sql.lower()   # bukan jangkauan proyek
    assert ":view_all" in sql and ":viewer" in sql
