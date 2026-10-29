"""
api/tests/modules/offboarding/test_offboarding_unit.py
Uji unit Milestone 9 tanpa DB (docs/35 §7): pembuatan offboarding, verifikasi barang, persetujuan PM & HR,
penyelesaian pada tanggal efektif, pembatalan.
"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.modules.offboarding.schemas.offboarding_schema import ClearanceItemVerify, OffboardingCreate
from app.modules.offboarding.services import offboarding_service as svc_mod
from app.modules.offboarding.services.offboarding_service import OffboardingService

EMP, DIV, PM, HR = str(uuid4()), str(uuid4()), str(uuid4()), str(uuid4())
TODAY = date(2026, 10, 21)


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setattr(svc_mod, "jakarta_now", lambda: SimpleNamespace(date=lambda: TODAY))


def _user(role: str, employee_id: str, permissions: tuple[str, ...] = ()) -> SimpleNamespace:
    held = {role}
    return SimpleNamespace(role=role, roles=[role], employee_id=employee_id, permissions=list(permissions),
                           has_role=lambda *names: any(name in held for name in names))


HR_USER = _user("ADMIN_HR_GA", HR, ("manage:offboarding", "view:offboarding"))
PM_USER = _user("PROJECT_MANAGER", PM, ("view:offboarding",))


def _record(**over):
    base = {"offboarding_id": uuid4(), "employee_id": EMP, "division_id": DIV, "status": "SUBMITTED",
            "is_all_assets_returned": True, "approved_by_pm_id": None, "approved_by_hr_id": None,
            "effective_date": TODAY, "_mapping": {}}
    base.update(over)
    return SimpleNamespace(**base)


def _service(record=None, employee=None, item=None):
    repo = MagicMock()
    repo.get = AsyncMock(return_value=record)
    repo.items = AsyncMock(return_value=[])
    repo.fetchall = AsyncMock(return_value=[SimpleNamespace(division_id=DIV)])  # divisi yang dipimpin PM
    repo.employee_for_offboarding = AsyncMock(return_value=employee)
    repo.open_for_employee = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=uuid4())
    repo.item_for_update = AsyncMock(return_value=item)
    repo.file_key = AsyncMock(return_value="files/serah.jpg")
    repo.verify_item = AsyncMock()
    repo.refresh_clearance = AsyncMock()
    repo.division_managers = AsyncMock(return_value=SimpleNamespace(pm_id=PM, om_id=None))
    repo.approve = AsyncMock()
    repo.finalize = AsyncMock()
    repo.cancel = AsyncMock()
    repo.due_for_completion = AsyncMock(return_value=[])
    assets = MagicMock()
    assets.return_loan = AsyncMock()
    return OffboardingService(repo, assets), repo, assets


def _employee(**over):
    base = {"offboarding_status": "active", "join_date": date(2025, 1, 1), "pkwt_end_date": date(2026, 12, 31),
            "leads_teams": None, "manages_divisions": None}
    base.update(over)
    return SimpleNamespace(**base)


async def test_create_uses_pkwt_end_date_and_blocks_open_roles():
    svc, repo, _ = _service(record=_record(), employee=_employee())
    await svc.create(OffboardingCreate(employee_id=EMP, reason_type="PKWT_EXPIRED"))
    assert repo.create.await_args.kwargs["effective_date"] == date(2026, 12, 31)

    svc, repo, _ = _service(employee=_employee(leads_teams="Tim MEP"))
    with pytest.raises(AppError) as err:
        await svc.create(OffboardingCreate(employee_id=EMP, reason_type="RESIGN", effective_date=TODAY))
    assert err.value.code == "HANDOVER_REQUIRED"
    repo.create.assert_not_awaited()

    svc, _, _ = _service(employee=_employee(offboarding_status="in_process"))
    with pytest.raises(AppError) as err:
        await svc.create(OffboardingCreate(employee_id=EMP, reason_type="RESIGN", effective_date=TODAY))
    assert err.value.code == "ALREADY_OFFBOARDING"

    svc, _, _ = _service(employee=_employee(pkwt_end_date=None))
    with pytest.raises(ValidationError):
        await svc.create(OffboardingCreate(employee_id=EMP, reason_type="PKWT_EXPIRED"))


def test_returned_goods_need_a_handover_photo():
    with pytest.raises(PydanticValidationError):
        ClearanceItemVerify(return_condition="GOOD")
    assert ClearanceItemVerify(return_condition="LOST").handover_file_id is None


async def test_verify_closes_the_loan_with_mapped_asset_status():
    item = SimpleNamespace(offboarding_id=uuid4(), assignment_id=uuid4(), verified_at=None,
                           status="CLEARANCE_PENDING", returned_at=None, division_id=DIV)
    svc, repo, assets = _service(record=_record(), item=item)
    await svc.verify_item(HR_USER, uuid4(), ClearanceItemVerify(return_condition="DAMAGED", handover_file_id=uuid4()))
    assets.return_loan.assert_awaited_once_with(item.assignment_id, "damaged")
    repo.refresh_clearance.assert_awaited_once_with(item.offboarding_id)

    # Sudah dikembalikan lewat menu aset: kondisi dicatat, pinjaman tidak ditutup dua kali.
    item.returned_at, item.verified_at = TODAY, None
    svc, _, assets = _service(record=_record(), item=item)
    await svc.verify_item(HR_USER, uuid4(), ClearanceItemVerify(return_condition="LOST"))
    assets.return_loan.assert_not_awaited()

    item.verified_at = TODAY
    svc, _, _ = _service(record=_record(), item=item)
    with pytest.raises(AppError) as err:
        await svc.verify_item(HR_USER, uuid4(), ClearanceItemVerify(return_condition="LOST"))
    assert err.value.code == "ALREADY_VERIFIED"


async def test_approval_requires_complete_clearance_and_right_roles():
    svc, _, _ = _service(record=_record(status="CLEARANCE_PENDING", is_all_assets_returned=False))
    with pytest.raises(AppError) as err:
        await svc.approve(HR_USER, uuid4(), "HR")
    assert err.value.code == "CLEARANCE_INCOMPLETE"

    svc, _, _ = _service(record=_record())
    with pytest.raises(ForbiddenError):
        await svc.approve(HR_USER, uuid4(), "PM")  # HR bukan PM/OM divisi
    with pytest.raises(ForbiddenError):
        await svc.approve(PM_USER, uuid4(), "HR")


async def test_both_approvals_finalize_when_effective_date_has_come():
    svc, repo, _ = _service(record=_record(approved_by_pm_id=PM, status="SUBMITTED"))
    repo.get = AsyncMock(side_effect=[_record(approved_by_pm_id=PM), _record(status="APPROVED"), _record()])
    await svc.approve(HR_USER, uuid4(), "HR")
    repo.finalize.assert_awaited_once()

    future = TODAY + timedelta(days=10)
    svc, repo, _ = _service()
    repo.get = AsyncMock(side_effect=[_record(approved_by_hr_id=HR), _record(status="APPROVED", effective_date=future),
                                      _record()])
    await svc.approve(PM_USER, uuid4(), "PM")
    repo.finalize.assert_not_awaited()  # menunggu penjadwal complete-due


async def test_pm_sees_only_own_division_and_cannot_cancel_completed():
    svc, _, _ = _service(record=_record(division_id=str(uuid4())))
    with pytest.raises(NotFoundError):
        await svc.detail(PM_USER, uuid4())


async def test_pm_with_two_divisions_sees_both_but_not_a_third():
    other = str(uuid4())
    svc, repo, _ = _service(record=_record(division_id=other))
    repo.fetchall = AsyncMock(return_value=[SimpleNamespace(division_id=DIV), SimpleNamespace(division_id=other)])
    assert (await svc.detail(PM_USER, uuid4()))["clearance_items"] == []  # divisi kedua tetap terlihat
    svc, repo, _ = _service(record=_record(division_id=str(uuid4())))
    repo.fetchall = AsyncMock(return_value=[SimpleNamespace(division_id=DIV), SimpleNamespace(division_id=other)])
    with pytest.raises(NotFoundError):
        await svc.detail(PM_USER, uuid4())
    svc, _, _ = _service(record=_record(status="COMPLETED"))
    with pytest.raises(AppError):
        await svc.cancel(HR_USER, uuid4(), "salah input")


async def test_complete_due_finalizes_each_due_record():
    svc, repo, _ = _service()
    repo.due_for_completion = AsyncMock(return_value=[SimpleNamespace(offboarding_id=uuid4(), employee_id=EMP)] * 2)
    assert await svc.complete_due() == 2
    assert repo.finalize.await_count == 2
