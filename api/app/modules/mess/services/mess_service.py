"""
app/modules/mess/services/mess_service.py
Hunian mess karyawan proyek. Mess dipilih dari master (company_mess), bukan diketik ulang. Karyawan mengajukan
hunian (REQUESTED) yang diputus PM divisinya / OM / HR; HR/GA juga dapat mencatat langsung (APPROVED). Karyawan
aktif; tanggal selesai ≥ mulai; tidak tumpang tindih dengan hunian aktif karyawan yang sama; kapasitas mess dijaga.
Lihat: view:mess; kelola: manage:mess (HR/GA); putuskan pengajuan: review:mess (PM/OM/HR).
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.core.time import jakarta_now, utcnow
from app.modules.mess.repositories.mess_repository import MessRepository
from app.modules.mess.schemas.mess_schema import (
    MessDecision,
    MessPlaceIn,
    MessPlaceUpdate,
    MessStayCreate,
    MessStayRequest,
    MessStayUpdate,
)
from app.modules.notifications.services.notification_service import NotificationService
from app.shared.access.office_scope import ensure_employee_in_scope, office_restriction, offices_param

ORG_WIDE_ROLES = ("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN")
MANAGER_ROLES = ("ADMIN_HR_GA", "SUPER_ADMIN")


def _period(start: date, end: date) -> str:
    return f"{start:%d/%m/%Y} - {end:%d/%m/%Y}"


class MessService:
    """Use case akomodasi mess."""

    def __init__(self, db: AsyncSession) -> None:
        self.repo = MessRepository(db)
        self.db = db

    # --- master mess ---------------------------------------------------------------------------------------------
    async def list_places(self) -> list[Any]:
        return await self.repo.list_places()

    async def get_place(self, mess_id: UUID) -> Any:
        place = await self.repo.get_place(mess_id)
        if place is None:
            raise NotFoundError("Mess")
        return place

    async def create_place(self, data: MessPlaceIn) -> Any:
        return await self.repo.get_place(await self.repo.insert_place(data.model_dump()))

    async def update_place(self, mess_id: UUID, data: MessPlaceUpdate) -> Any:
        await self.get_place(mess_id)
        await self.repo.update_place(mess_id, data.model_dump())
        return await self.repo.get_place(mess_id)

    async def delete_place(self, mess_id: UUID) -> None:
        await self.get_place(mess_id)
        if await self.repo.place_has_active_stays(mess_id):
            raise AppError("MESS_IN_USE", "Mess masih dihuni atau punya pengajuan aktif; selesaikan dulu hunian itu.",
                           status=409)
        await self.repo.archive_place(mess_id)

    # --- hunian ----------------------------------------------------------------------------------------------------
    async def _offices(self, user: CurrentUser | None) -> list[str] | None:
        """None = semua kantor. HR (bukan SA/OM) dibatasi ke kantor jangkauannya bila ROLE_ASSIGNMENT_ENABLED."""
        if user is None:
            return None
        restriction = await office_restriction(self.db, user, Permission.MANAGE_MESS,
                                               ("SUPER_ADMIN", "OPERATIONAL_MANAGER"))
        return None if restriction is None else offices_param(restriction)

    async def _ensure_employee(self, user: CurrentUser | None, employee_id: UUID | str) -> None:
        if user is not None and await self._offices(user) is not None:
            await ensure_employee_in_scope(self.db, user, Permission.MANAGE_MESS, employee_id, "Hunian mess")

    async def list_stays(
        self, employee_id: UUID | None, start: date | None, end: date | None, status: str | None = None,
        user: CurrentUser | None = None,
    ) -> list[Any]:
        return await self.repo.list_stays(employee_id, start, end, status, await self._offices(user))

    async def get_stay(self, mess_stay_id: UUID, user: CurrentUser | None = None) -> Any:
        stay = await self.repo.get(mess_stay_id)
        if stay is None:
            raise NotFoundError("Hunian mess")
        await self._ensure_employee(user, stay.employee_id)
        return stay

    async def _check_period(self, employee_id: UUID | str, start: date, end: date,
                            exclude: UUID | None = None) -> None:
        if end < start:
            raise ValidationError("Tanggal selesai menginap tidak boleh sebelum tanggal mulai.")
        if await self.repo.overlaps(employee_id, start, end, exclude):
            raise AppError("MESS_OVERLAP", "Karyawan ini sudah punya hunian atau pengajuan mess pada tanggal tersebut.",
                           status=409)

    async def _check_capacity(self, place: Any, start: date, end: date, exclude: UUID | None = None) -> None:
        """Kapasitas dijaga per tanggal: tidak boleh ada tanggal dalam rentang yang sudah penuh."""
        if place.capacity is None:
            return
        full_on = await self.repo.first_full_day(place.mess_id, start, end, place.capacity, exclude)
        if full_on is not None:
            raise AppError("MESS_FULL", f"Mess penuh pada {full_on:%d-%m-%Y} (kapasitas {place.capacity} orang).",
                           status=409)

    async def _check_team(self, team_id: UUID | None) -> str | None:
        if team_id is None:
            return None
        if not await self.repo.team_exists(team_id):
            raise ValidationError("Tim tidak ditemukan.")
        return str(team_id)

    async def create_stay(self, user: CurrentUser, data: MessStayCreate) -> Any:
        """Pencatatan langsung HR/GA: langsung disetujui."""
        await self._ensure_employee(user, data.employee_id)
        if not await self.repo.employee_active(data.employee_id):
            raise ValidationError("Karyawan tidak ditemukan atau tidak aktif.")
        place = await self.get_place(data.mess_id)
        await self._check_period(data.employee_id, data.stay_start_date, data.stay_end_date)
        await self._check_capacity(place, data.stay_start_date, data.stay_end_date)
        stay_id = await self.repo.insert({
            "mess_id": str(data.mess_id), "employee_id": str(data.employee_id),
            "stay_start_date": data.stay_start_date, "stay_end_date": data.stay_end_date, "status": "APPROVED",
            "requested_by": None, "request_note": None, "decided_by": user.user_id,
            "decided_at": utcnow(), "team_id": await self._check_team(data.team_id),
        })
        await NotificationService(self.db).notify_employees(
            [data.employee_id], "MESS_ASSIGNED", f"Anda ditempatkan di {place.mess_name}",
            f"{_period(data.stay_start_date, data.stay_end_date)}, {place.address}", target="mess",
        )
        return await self.repo.get(stay_id)

    async def request_stay(self, user: CurrentUser, data: MessStayRequest) -> Any:
        """Karyawan mengajukan hunian di mess pilihannya."""
        if user.employee_id is None:
            raise ForbiddenError("Akun ini tidak tertaut ke data karyawan.")
        employee_id = UUID(str(user.employee_id))
        if not await self.repo.employee_active(employee_id):
            raise ValidationError("Karyawan tidak ditemukan atau tidak aktif.")
        if data.stay_start_date < jakarta_now().date():
            raise ValidationError("Tanggal mulai tidak boleh di masa lalu.")
        place = await self.get_place(data.mess_id)
        await self._check_period(employee_id, data.stay_start_date, data.stay_end_date)
        await self._check_capacity(place, data.stay_start_date, data.stay_end_date)
        stay_id = await self.repo.insert({
            "mess_id": str(data.mess_id), "employee_id": str(employee_id),
            "stay_start_date": data.stay_start_date, "stay_end_date": data.stay_end_date, "status": "REQUESTED",
            "team_id": await self._check_team(data.team_id),
            "requested_by": user.user_id, "request_note": (data.note or "").strip() or None,
            "decided_by": None, "decided_at": None,
        })
        stay = await self.repo.get(stay_id)
        notifier = NotificationService(self.db)
        who = await notifier.employee_name(employee_id) or "Karyawan"
        title = f"{who} mengajukan hunian di {place.mess_name}"
        body = _period(data.stay_start_date, data.stay_end_date)
        await notifier.notify_division_managers(employee_id, "MESS_REQUESTED", title, body, target="mess")
        await notifier.notify_roles(("ADMIN_HR_GA",), "MESS_REQUESTED", title, body, target="mess")
        return stay

    async def _can_decide(self, user: CurrentUser, employee_id: UUID | str) -> bool:
        if user.has_role(*ORG_WIDE_ROLES):
            return True
        if user.has_role("PROJECT_MANAGER"):
            pm_id = await self.repo.division_pm_of(employee_id)
            return pm_id is not None and str(pm_id) == str(user.employee_id)
        return False

    async def decide(self, user: CurrentUser, mess_stay_id: UUID, data: MessDecision) -> Any:
        stay = await self.get_stay(mess_stay_id, user)
        if str(user.employee_id) == str(stay.employee_id):
            raise ForbiddenError("Pemohon tidak dapat memutuskan pengajuannya sendiri.")
        if not await self._can_decide(user, stay.employee_id):
            raise ForbiddenError("Anda tidak berwenang memutuskan pengajuan mess karyawan ini.")
        if stay.status != "REQUESTED":
            raise AppError("MESS_ALREADY_DECIDED", "Pengajuan ini sudah diputuskan atau dibatalkan.", status=409)
        note = (data.note or "").strip() or None
        if not data.approve and note is None:
            raise ValidationError("Alasan penolakan wajib diisi.")
        if data.approve:
            place = await self.get_place(stay.mess_id) if stay.mess_id else None
            if place is not None:
                await self._check_capacity(place, stay.stay_start_date, stay.stay_end_date, exclude=mess_stay_id)
            await self._check_period(stay.employee_id, stay.stay_start_date, stay.stay_end_date, exclude=mess_stay_id)
        status = "APPROVED" if data.approve else "REJECTED"
        # Kondisi status ada di UPDATE: dua peninjau bersamaan tidak sama-sama lolos.
        if not await self.repo.decide(mess_stay_id, status, user.user_id, note, utcnow()):
            raise AppError("MESS_ALREADY_DECIDED", "Pengajuan ini sudah diputuskan atau dibatalkan.", status=409)
        notifier = NotificationService(self.db)
        who = await notifier.employee_name(user.employee_id) if user.employee_id else None
        await notifier.notify_employees(
            [stay.employee_id], "MESS_DECIDED",
            f"Pengajuan mess {'disetujui' if data.approve else 'ditolak'}" + (f" oleh {who}" if who else ""),
            f"{stay.mess_name}, {_period(stay.stay_start_date, stay.stay_end_date)}"
            + (f". Catatan: {note}" if note else ""),
            target="mess",
        )
        return await self.repo.get(mess_stay_id)

    def _is_owner(self, user: CurrentUser, stay: Any) -> bool:
        return user.employee_id is not None and str(user.employee_id) == str(stay.employee_id)

    async def cancel(self, user: CurrentUser, mess_stay_id: UUID) -> Any:
        """Pemohon membatalkan pengajuan (atau hunian yang belum dimulai); HR/GA boleh membatalkan siapa pun."""
        stay = await self.get_stay(mess_stay_id, user)
        if not (self._is_owner(user, stay) or user.has_role(*MANAGER_ROLES)):
            raise ForbiddenError("Hanya pemohon atau HR/GA yang dapat membatalkan hunian ini.")
        not_started = stay.stay_start_date > jakarta_now().date()
        cancellable = stay.status == "REQUESTED" or (stay.status == "APPROVED" and not_started)
        if not cancellable:
            raise AppError("MESS_NOT_CANCELLABLE", "Hunian yang sudah berjalan tidak dapat dibatalkan; pakai "
                           "\"Selesai inap\".", status=409)
        if not await self.repo.set_status(mess_stay_id, "CANCELLED", allowed=("REQUESTED", "APPROVED")):
            raise AppError("MESS_NOT_CANCELLABLE", "Status pengajuan sudah berubah; muat ulang.", status=409)
        if stay.status == "APPROVED" and not self._is_owner(user, stay):
            await NotificationService(self.db).notify_employees(
                [stay.employee_id], "MESS_CANCELLED", f"Hunian di {stay.mess_name} dibatalkan",
                _period(stay.stay_start_date, stay.stay_end_date), target="mess",
            )
        return await self.repo.get(mess_stay_id)

    async def end_stay(self, user: CurrentUser, mess_stay_id: UUID) -> Any:
        """Selesai inap: tanggal selesai dimajukan ke hari ini (riwayat tetap ada)."""
        stay = await self.get_stay(mess_stay_id, user)
        if not (self._is_owner(user, stay) or user.has_role(*MANAGER_ROLES)):
            raise ForbiddenError("Hanya penghuni atau HR/GA yang dapat menyelesaikan hunian ini.")
        today = jakarta_now().date()
        if stay.status != "APPROVED" or stay.stay_start_date > today or stay.stay_end_date < today:
            raise AppError("MESS_NOT_ACTIVE", "Hanya hunian yang sedang berjalan yang dapat diselesaikan.", status=409)
        await self.repo.set_end_date(mess_stay_id, today)
        return await self.repo.get(mess_stay_id)

    async def update_stay(self, mess_stay_id: UUID, data: MessStayUpdate, user: CurrentUser | None = None) -> Any:
        stay = await self.get_stay(mess_stay_id, user)
        start = data.stay_start_date or stay.stay_start_date
        end = data.stay_end_date or stay.stay_end_date
        await self._check_period(stay.employee_id, start, end, exclude=mess_stay_id)
        if stay.mess_id and stay.status == "APPROVED":
            await self._check_capacity(await self.get_place(stay.mess_id), start, end, exclude=mess_stay_id)
        await self.repo.update_dates(mess_stay_id, data.stay_start_date, data.stay_end_date)
        return await self.repo.get(mess_stay_id)

    async def delete_stay(self, mess_stay_id: UUID, user: CurrentUser | None = None) -> None:
        await self.get_stay(mess_stay_id, user)
        await self.repo.archive(mess_stay_id)
