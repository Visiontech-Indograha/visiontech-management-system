"""Admin perangkat Hikvision: perangkat, token penerima, pemetaan nomor perangkat ke karyawan, status.

Cakupan: SUPER_ADMIN, OPERATIONAL_MANAGER (dan ADMIN lama) semua kantor; HR/Admin HR GA hanya kantornya sendiri
(ditambah kantor penugasan bila peran ganda aktif). Objek di luar cakupan dijawab 404. Kredensial perangkat untuk
tarik TIDAK disimpan di sini (tetap dari lingkungan/berkas rahasia). Token hanya muncul sekali (disimpan hash)."""
from __future__ import annotations

import secrets
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.core.permissions import Permission, RoleCode, SystemRole
from app.core.security import CurrentUser
from app.core.time import utcnow
from app.modules.hikvision.repositories.hikvision_admin_repository import HikvisionAdminRepository
from app.modules.hikvision.repositories.hikvision_proses_repository import HikvisionProsesRepository
from app.modules.hikvision.schemas import admin as s
from app.modules.hikvision.services import konstanta as hk
from app.modules.hikvision.services.penerima_service import hash_token
from app.shared.access.office_scope import office_restriction

_PATH = "/api/v1/hikvision/events/{token}"
_BATCH = 5000
_MAX_BATCH_PER_PANGGILAN = 20
_JENDELA_USULAN_HARI = 90
_MAKS_USULAN = 500
_MAKS_BANDING = 500
_ALASAN = "Tidak ada karyawan dengan nomor ini di kantor perangkat."


class Cakupan:
    def __init__(self, semua: bool, offices: list[str]) -> None:
        self.semua = semua
        self.offices = offices

    def boleh(self, office_id: Any) -> bool:
        return self.semua or str(office_id) in self.offices


class HikvisionAdminService:
    def __init__(self, repo: HikvisionAdminRepository, db: AsyncSession) -> None:
        self.repo = repo
        self.db = db

    async def cakupan(self, user: CurrentUser) -> Cakupan:
        if user.has_role(SystemRole.SUPER_ADMIN.value, SystemRole.OPERATIONAL_MANAGER.value, RoleCode.ADMIN.value):
            return Cakupan(True, [])
        kantor: set[str] = {user.office_id} if user.office_id else set()
        tambahan = await office_restriction(self.db, user, Permission.MANAGE_HIKVISION)
        if tambahan:
            kantor |= set(tambahan)
        return Cakupan(False, sorted(kantor))

    async def _perangkat(self, device_id: UUID, user: CurrentUser) -> tuple[Any, Cakupan]:
        c = await self.cakupan(user)
        row = await self.repo.device(str(device_id), c.semua, c.offices)
        if row is None:
            raise NotFoundError("Perangkat")
        return row, c

    @staticmethod
    def _token_baru(device_id: Any, base_url: str) -> tuple[str, s.TokenBaru]:
        token = secrets.token_urlsafe(32)
        path = _PATH.format(token=token)
        return hash_token(token), s.TokenBaru(
            device_id=device_id, token=token, receiver_url=base_url.rstrip("/") + path, receiver_path=path
        )

    # ---- perangkat ----
    async def daftar(self, user: CurrentUser, office_id: UUID | None) -> list[s.PerangkatOut]:
        c = await self.cakupan(user)
        rows = await self.repo.devices(c.semua, c.offices, str(office_id) if office_id else None)
        return [s.PerangkatOut.model_validate(r, from_attributes=True) for r in rows]

    async def detail(self, device_id: UUID, user: CurrentUser) -> s.PerangkatOut:
        row, _ = await self._perangkat(device_id, user)
        return s.PerangkatOut.model_validate(row, from_attributes=True)

    async def buat(self, body: s.PerangkatBuat, user: CurrentUser, base_url: str) -> s.PerangkatDibuat:
        c = await self.cakupan(user)
        if not c.boleh(body.office_id) or await self.repo.office(str(body.office_id)) is None:
            raise NotFoundError("Kantor")
        h, penerima = self._token_baru("00000000-0000-0000-0000-000000000000", base_url)
        new_id = await self.repo.insert_device({**body.model_dump(mode="json")}, h, utcnow())
        if new_id is None:
            raise AppError("CONFLICT", "Nomor seri ini sudah dipakai perangkat lain.", status=409)
        penerima.device_id = UUID(new_id)
        row = await self.repo.device(new_id, c.semua, c.offices)
        return s.PerangkatDibuat(perangkat=s.PerangkatOut.model_validate(row, from_attributes=True), penerima=penerima)

    async def ubah(self, device_id: UUID, body: s.PerangkatUbah, user: CurrentUser) -> s.PerangkatOut:
        await self._perangkat(device_id, user)
        changes = body.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is None:
            changes.pop("name")
        for wajib in ("ip_address", "http_port", "serial_no", "mode", "aktif"):
            if wajib in changes and changes[wajib] is None:
                changes.pop(wajib)
        if changes and not await self.repo.update_device(str(device_id), changes, utcnow()):
            raise AppError("CONFLICT", "Nomor seri ini sudah dipakai perangkat lain.", status=409)
        return await self.detail(device_id, user)

    async def hapus(self, device_id: UUID, user: CurrentUser) -> None:
        await self._perangkat(device_id, user)
        await self.repo.soft_delete_device(str(device_id), utcnow())

    async def ganti_token(self, device_id: UUID, user: CurrentUser, base_url: str) -> s.TokenBaru:
        await self._perangkat(device_id, user)
        h, penerima = self._token_baru(device_id, base_url)
        await self.repo.set_token_hash(str(device_id), h, utcnow())
        return penerima

    # ---- pemetaan ----
    async def daftar_pemetaan(self, device_id: UUID, user: CurrentUser) -> list[s.PemetaanOut]:
        await self._perangkat(device_id, user)
        rows = await self.repo.maps(str(device_id))
        return [s.PemetaanOut.model_validate(r, from_attributes=True) for r in rows]

    async def _karyawan_dalam_cakupan(self, employee_id: UUID, c: Cakupan) -> None:
        emp = await self.repo.employee_office(str(employee_id))
        if emp is None or not c.boleh(emp.office_id):
            raise NotFoundError("Karyawan")

    async def buat_pemetaan(self, device_id: UUID, body: s.PemetaanBuat, user: CurrentUser) -> s.PemetaanOut:
        _, c = await self._perangkat(device_id, user)
        await self._karyawan_dalam_cakupan(body.employee_id, c)
        map_id = await self.repo.insert_map(str(device_id), body.employee_no_string, str(body.employee_id))
        if map_id is None:
            raise AppError("CONFLICT", "Nomor ini sudah dipetakan ke karyawan lain di perangkat ini.", status=409)
        row = await self.repo.map_by_id(str(device_id), map_id)
        return s.PemetaanOut.model_validate(row, from_attributes=True)

    async def ubah_pemetaan(
        self, device_id: UUID, map_id: UUID, body: s.PemetaanUbah, user: CurrentUser
    ) -> s.PemetaanOut:
        _, c = await self._perangkat(device_id, user)
        if await self.repo.map_by_id(str(device_id), str(map_id)) is None:
            raise NotFoundError("Pemetaan")
        await self._karyawan_dalam_cakupan(body.employee_id, c)
        await self.repo.update_map(str(device_id), str(map_id), str(body.employee_id))
        row = await self.repo.map_by_id(str(device_id), str(map_id))
        return s.PemetaanOut.model_validate(row, from_attributes=True)

    async def hapus_pemetaan(self, device_id: UUID, map_id: UUID, user: CurrentUser) -> None:
        await self._perangkat(device_id, user)
        if not await self.repo.delete_map(str(device_id), str(map_id), utcnow()):
            raise NotFoundError("Pemetaan")

    async def _usulan(self, device: Any) -> s.UsulanPemetaan:
        sejak = utcnow() - timedelta(days=_JENDELA_USULAN_HARI)
        belum = await self.repo.unmapped_numbers(str(device.device_id), sejak, _MAKS_USULAN)
        nomor = [r.employee_no_string for r in belum]
        emp = {e.employee_no: e for e in await self.repo.employees_by_no(str(device.office_id), nomor)} if nomor else {}
        cocok: list[s.UsulanCocok] = []
        tak: list[s.UsulanTakCocok] = []
        for r in belum:
            e = emp.get(r.employee_no_string)
            if e is None:
                tak.append(s.UsulanTakCocok(
                    employee_no_string=r.employee_no_string, jumlah_event=int(r.jumlah), alasan=_ALASAN))
            else:
                cocok.append(s.UsulanCocok(
                    employee_no_string=r.employee_no_string, employee_id=e.employee_id,
                    employee_no=e.employee_no, full_name=e.full_name, jumlah_event=int(r.jumlah)))
        return s.UsulanPemetaan(cocok=cocok, tidak_cocok=tak)

    async def usulan(self, device_id: UUID, user: CurrentUser) -> s.UsulanPemetaan:
        device, _ = await self._perangkat(device_id, user)
        return await self._usulan(device)

    async def _terapkan(self, device_id: str) -> tuple[int, bool]:
        total = 0
        for _ in range(_MAX_BATCH_PER_PANGGILAN):
            n = await self.repo.apply_maps_to_events(device_id, _BATCH)
            total += n
            if n < _BATCH:
                return total, False
        return total, True

    async def terapkan(self, device_id: UUID, user: CurrentUser) -> s.PemetaanDiterapkan:
        await self._perangkat(device_id, user)
        n, sisa = await self._terapkan(str(device_id))
        return s.PemetaanDiterapkan(event_diperbarui=n, masih_ada_sisa=sisa)

    async def otomatis(self, device_id: UUID, user: CurrentUser) -> s.PemetaanOtomatisOut:
        device, _ = await self._perangkat(device_id, user)
        u = await self._usulan(device)
        dibuat = await self.repo.insert_maps_bulk(
            str(device_id), [{"no": c.employee_no_string, "emp": str(c.employee_id)} for c in u.cocok]
        )
        n, sisa = await self._terapkan(str(device_id))
        return s.PemetaanOtomatisOut(dibuat=dibuat, event_diperbarui=n, masih_ada_sisa=sisa, tidak_cocok=u.tidak_cocok)

    # ---- status ----
    async def status(self, device_id: UUID, user: CurrentUser) -> s.StatusPerangkat:
        d, _ = await self._perangkat(device_id, user)
        now = utcnow()
        t7 = now - timedelta(days=7)
        cnt = await self.repo.event_counts(str(device_id), now - timedelta(hours=24), t7)
        return s.StatusPerangkat(
            device_id=d.device_id, mode=d.mode, aktif=d.aktif,
            event_24_jam=int(cnt.c24 or 0), event_7_hari=int(cnt.c7 or 0),
            event_terakhir_diterima=await self.repo.last_received(str(device_id)),
            belum_terpetakan_7_hari=int(cnt.belum or 0),
            kemungkinan_duplikat_7_hari=await self.repo.duplicate_groups(str(device_id), t7),
        )

    async def banding_bayangan(self, device_id: UUID, dari: date, sampai: date, user: CurrentUser) -> s.BandingBayangan:
        row, _ = await self._perangkat(device_id, user)
        repo = HikvisionProsesRepository(self.db)
        rows, r = await repo.banding_perangkat(
            str(device_id), dari, sampai, _MAKS_BANDING, hk.MAJOR_AKSES, sorted(hk.MINOR_VERIFIKASI_LOLOS))
        return s.BandingBayangan(
            device_id=device_id, mode=row.mode, dari=dari, sampai=sampai,
            akan_menghasilkan_absen=int(r.akan_dihasilkan), total_karyawan_hari=int(r.total),
            tak_terpetakan=int(r.tak_terpetakan), terpotong=int(r.total) > len(rows),
            items=[s.BandingBaris.model_validate(x, from_attributes=True) for x in rows],
        )
