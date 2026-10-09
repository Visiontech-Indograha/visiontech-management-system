"""
app/services/notification_service.py
Notifikasi dalam aplikasi untuk tahap SK (alur SK v2, flowchart SK2): terbit → ketua & anggota,
adendum diminta → PM, diterima → PM & anggota, mulai berjalan → semua yang terikat.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.crud.crud_notification import CRUDNotification


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "ya" if value else "tidak"
    return str(value)


def diff_summary(diff: list[dict[str, Any]], limit: int = 3) -> str:
    """Ringkasan diff revisi, maksimal `limit` butir. Contoh: "Tanggal selesai 2026-10-12 → 2026-10-14; anggota:
    +Andi, -Budi." """
    parts: list[str] = []
    for d in diff:
        if d["field"] in ("members", "assets"):
            names = [f"+{n}" for n in d.get("added", [])] + [f"-{n}" for n in d.get("removed", [])]
            parts.append(f"{str(d['label']).lower()}: {', '.join(names)}")
        elif d["field"] == "days":
            changes = len(d.get("added", [])) + len(d.get("removed", [])) + len(d.get("changed", []))
            parts.append(f"{changes} hari kerja berubah")
        else:
            parts.append(f"{d['label']} {_fmt(d.get('before'))} → {_fmt(d.get('after'))}")
    text = "; ".join(parts[:limit])
    if len(parts) > limit:
        text += f"; dan {len(parts) - limit} perubahan lain"
    return text + "."


class NotificationService:
    """Layanan sentral pengiriman dan pengelolaan notifikasi dalam sistem aplikasi."""

    def __init__(self, db: AsyncSession) -> None:
        self.repo = CRUDNotification(db)

    async def _plan(self, plan_id: UUID | str) -> Any:
        """
        Mencari data personel yang terhubung dengan suatu Surat Keputusan (SK).

        Args:
            plan_id: ID dari SK.

        Returns:
            Any: Data detail pihak-pihak terkait dari repo.

        Raises:
            NotFoundError: Jika SK tidak ada.
        """
        people = await self.repo.plan_people(plan_id)
        if people is None:
            raise NotFoundError("Rencana Kerja")
        return people

    @staticmethod
    def _label(people: Any) -> str:
        """
        Membuat teks label untuk keperluan subjek notifikasi.
        """
        return str(people.number) if people.number else "Rencana Kerja"   # nomor sudah berawalan "SK-"

    async def _actor(self) -> str:
        """Nama karyawan pelaku (pengguna yang sedang masuk), dibaca dari konteks sesi `app.user_id`."""
        name = await self.repo.scalar(
            "SELECT e.full_name FROM vms.app_user u JOIN vms.employee e ON e.id = u.employee_id "
            "WHERE u.id = NULLIF(current_setting('app.user_id', true), '')::uuid")
        return str(name) if name else "PM"

    @staticmethod
    def _span(p: Any) -> str:
        """Rentang tanggal ringkas: "12–14 Okt" atau "12 Okt" (satu hari)."""
        start, end = p.period_start, p.period_end
        month = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")
        if start == end:
            return f"{start.day} {month[start.month - 1]}"
        if start.month == end.month:
            return f"{start.day}–{end.day} {month[end.month - 1]}"
        return f"{start.day} {month[start.month - 1]} – {end.day} {month[end.month - 1]}"

    async def plan_published(self, plan_id: UUID | str) -> None:
        """
        Mengirim notifikasi ketika rencana kerja diterbitkan: ketua diminta meninjau, anggota diberi tahu.

        Args:
            plan_id: ID rencana kerja.
        """
        p = await self._plan(plan_id)
        actor, head = await self._actor(), f"{p.title}, {self._span(p)}."
        title = f"{actor} menerbitkan {self._label(p)}"
        await self.repo.insert_many(p.organization_id, [p.leader], "PLAN_PUBLISHED", title,
                                    f"{head} Anda ketua tim: tinjau lalu terima, atau ajukan revisi.", plan_id)
        await self.repo.insert_many(p.organization_id, p.members, "PLAN_PUBLISHED", title,
                                    f"{head} Anda anggota tim.", plan_id)

    async def amendment_requested(self, plan_id: UUID | str, reason: str) -> None:
        """
        Mengirim notifikasi permintaan adendum SK oleh tim di lapangan kepada PM.

        Args:
            plan_id: ID SK.
            reason: Alasan permintaan adendum.
        """
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm], "PLAN_AMENDMENT_REQUESTED",
                                    f"{await self._actor()} meminta revisi {self._label(p)}",
                                    f"{p.title}. Alasan: {reason}", plan_id)

    async def plan_accepted(self, plan_id: UUID | str) -> None:
        """
        Mengirim notifikasi ketika SK telah diterima oleh ketua tim.

        Args:
            plan_id (UUID | str): ID SK terkait.
        """
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm, *p.members], "PLAN_ACCEPTED",
                                    f"{await self._actor()} menerima {self._label(p)}",
                                    f"{p.title} — berjalan otomatis pada tanggal mulai.", plan_id)

    async def plan_started(self, plan_id: UUID | str) -> None:
        """
        Mengirim notifikasi ketika SK mulai berjalan.

        Args:
            plan_id (UUID | str): ID SK terkait.
        """
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm, p.leader, *p.members], "PLAN_STARTED",
                                    f"{self._label(p)} mulai berjalan", p.title, plan_id)

    async def list_for(self, user_id: str, unread_only: bool = False, limit: int = 50) -> list[Any]:
        """
        Mengambil daftar notifikasi untuk pengguna tertentu.

        Args:
            user_id (str): ID pengguna.
            unread_only (bool): Jika True, hanya ambil notifikasi yang belum dibaca.
            limit (int): Batas jumlah notifikasi (default 50).

        Returns:
            list[Any]: Daftar objek notifikasi.
        """
        return await self.repo.list_for(user_id, unread_only, min(max(limit, 1), 100))

    async def unread_count(self, user_id: str) -> int:
        """
        Menghitung jumlah notifikasi yang belum dibaca oleh pengguna.

        Args:
            user_id (str): ID pengguna.

        Returns:
            int: Jumlah notifikasi belum dibaca.
        """
        return await self.repo.unread_count(user_id)

    async def mark_read(self, user_id: str, notification_id: UUID | None) -> int:
        """
        Menandai notifikasi sebagai telah dibaca.

        Args:
            user_id (str): ID pengguna.
            notification_id (UUID | None): ID notifikasi tunggal (atau None untuk semua).

        Returns:
            int: Jumlah baris yang diperbarui.
        """
        return await self.repo.mark_read(user_id, notification_id)

    # ── Laporan berjenjang (PR2) ─────────────────────────────────────────────────────────────
    async def member_report_sent(self, plan_id: UUID | str, member_name: str, work_date: Any) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.leader], "MEMBER_REPORT_SENT",
                                    f"{member_name} mengirim laporan {work_date:%d-%m-%Y}",
                                    f"{p.title} ({self._label(p)}) — menunggu Anda memeriksa.", plan_id)

    async def report_submitted(self, plan_id: UUID | str, what: str, resubmitted: bool) -> None:
        p = await self._plan(plan_id)
        verb = "mengirim ulang" if resubmitted else "mengirim"
        await self.repo.insert_many(p.organization_id, [p.pm], "REPORT_SUBMITTED",
                                    f"{await self._actor()} {verb} {what} {self._label(p)}",
                                    f"{p.title} — menunggu pemeriksaan PM.", plan_id)

    async def report_reviewed(self, plan_id: UUID | str, what: str, approved: bool, note: str | None) -> None:
        p = await self._plan(plan_id)
        title = f"{await self._actor()} {'menyetujui' if approved else 'mengembalikan'} {what} {self._label(p)}"
        await self.repo.insert_many(p.organization_id, [p.leader], "REPORT_REVIEWED", title,
                                    note or p.title, plan_id)

    # ── Adendum saat berjalan & penutupan (PR3) ──────────────────────────────────────────────
    async def amendment_decided(self, plan_id: UUID | str, *, accepted: bool, note: str | None) -> None:
        p = await self._plan(plan_id)
        if accepted:
            title = f"{await self._actor()} menyiapkan revisi {self._label(p)}"
            body = f"{p.title} — isi rencana kerja sudah diubah. Tinjau lalu terima revisi."
        else:
            title = f"{await self._actor()} menolak permintaan revisi {self._label(p)}"
            body = f"Catatan: {note}" if note else p.title
        await self.repo.insert_many(p.organization_id, [p.leader], "AMENDMENT_DECIDED", title, body, plan_id)

    async def plan_revised(self, plan_id: UUID | str, actor_name: str, reason: str, diff: list[dict[str, Any]],
                           recipients: Iterable[str]) -> None:
        """Revisi PM (T6): ketua serta anggota lama dan baru diberi tahu apa yang berubah."""
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, recipients, "PLAN_REVISED",
                                    f"{actor_name} merevisi {self._label(p)}",
                                    f"{diff_summary(diff)} Alasan: {reason}", plan_id)

    async def attendance_flagged(self, org_id: str, reviewers: Iterable[str], title: str) -> None:
        """Absen Perlu review (mis. "Absen pulang Andi di luar radius (420 m)") → PM/peninjau berwenang."""
        await self.repo.insert_many(org_id, reviewers, "ATTENDANCE_FLAGGED", title,
                                    "Periksa di menu Absensi.", None)

    async def attendance_decided(self, org_id: str, employee_id: str, approved: bool, note: str) -> None:
        """Keputusan peninjau atas absensi → karyawannya."""
        verb = "menyetujui" if approved else "menolak"
        await self.repo.insert_many(org_id, [employee_id], "ATTENDANCE_DECIDED",
                                    f"{await self._actor()} {verb} absensi Anda", f"Catatan: {note}", None)

    async def amendment_accepted(self, plan_id: UUID | str) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm, *p.members], "AMENDMENT_ACCEPTED",
                                    f"{await self._actor()} menerima revisi {self._label(p)}",
                                    f"{p.title} — versi sebelumnya tidak berlaku lagi.", plan_id)

    async def completion_requested(self, plan_id: UUID | str) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm], "COMPLETION_REQUESTED",
                                    f"{await self._actor()} mengajukan penutupan {self._label(p)}",
                                    f"{p.title} — laporan akhir menunggu pemeriksaan.", plan_id)

    async def completion_decided(self, plan_id: UUID | str, *, approved: bool, note: str | None) -> None:
        p = await self._plan(plan_id)
        if approved:
            await self.repo.insert_many(p.organization_id, [p.leader, *p.members], "PLAN_COMPLETED",
                                        f"{await self._actor()} menutup {self._label(p)}",
                                        f"{p.title} — selesai; tim dan aset sudah dilepas.", plan_id)
        else:
            await self.repo.insert_many(p.organization_id, [p.leader], "COMPLETION_RETURNED",
                                        f"{await self._actor()} mengembalikan laporan akhir {self._label(p)}",
                                        f"Catatan: {note}" if note else p.title, plan_id)
