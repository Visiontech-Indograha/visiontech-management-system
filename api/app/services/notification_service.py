"""
app/services/notification_service.py
Notifikasi dalam aplikasi untuk tahap SK (alur SK v2, flowchart SK2): terbit → ketua & anggota,
adendum diminta → PM, diterima → PM & anggota, mulai berjalan → semua yang terikat.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.crud.crud_notification import CRUDNotification


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = CRUDNotification(db)

    async def _plan(self, plan_id: UUID | str) -> Any:
        people = await self.repo.plan_people(plan_id)
        if people is None:
            raise NotFoundError("SK")
        return people

    @staticmethod
    def _label(people: Any) -> str:
        return str(people.number) if people.number else "SK"   # nomor sudah berawalan "SK-"

    async def plan_published(self, plan_id: UUID | str) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(
            p.organization_id, [p.leader, *p.members], "PLAN_PUBLISHED", f"{self._label(p)} terbit",
            f"{p.title} — ketua tim diminta meninjau lalu menerima SK atau mengajukan adendum.", plan_id)

    async def amendment_requested(self, plan_id: UUID | str, reason: str) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm], "PLAN_AMENDMENT_REQUESTED",
                                    f"Adendum diminta: {self._label(p)}", f"{p.title} — alasan: {reason}", plan_id)

    async def plan_accepted(self, plan_id: UUID | str) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm, *p.members], "PLAN_ACCEPTED",
                                    f"{self._label(p)} diterima ketua tim",
                                    f"{p.title} — berjalan otomatis pada tanggal mulai.", plan_id)

    async def plan_started(self, plan_id: UUID | str) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm, p.leader, *p.members], "PLAN_STARTED",
                                    f"{self._label(p)} mulai berjalan", p.title, plan_id)

    async def list_for(self, user_id: str, unread_only: bool = False, limit: int = 50) -> list[Any]:
        return await self.repo.list_for(user_id, unread_only, min(max(limit, 1), 100))

    async def unread_count(self, user_id: str) -> int:
        return await self.repo.unread_count(user_id)

    async def mark_read(self, user_id: str, notification_id: UUID | None) -> int:
        return await self.repo.mark_read(user_id, notification_id)

    # ── Laporan berjenjang (PR2) ─────────────────────────────────────────────────────────────
    async def member_report_sent(self, plan_id: UUID | str, member_name: str, work_date: Any) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.leader], "MEMBER_REPORT_SENT",
                                    f"Laporan anggota masuk: {self._label(p)}",
                                    f"{member_name} mengirim laporan {work_date:%d-%m-%Y}.", plan_id)

    async def report_submitted(self, plan_id: UUID | str, what: str, resubmitted: bool) -> None:
        p = await self._plan(plan_id)
        verb = "dikirim ulang" if resubmitted else "dikirim"
        await self.repo.insert_many(p.organization_id, [p.pm], "REPORT_SUBMITTED",
                                    f"{what} {verb}: {self._label(p)}", f"{p.title} — menunggu pemeriksaan PM.", plan_id)

    async def report_reviewed(self, plan_id: UUID | str, what: str, approved: bool, note: str | None) -> None:
        p = await self._plan(plan_id)
        title = f"{what} {'disetujui' if approved else 'perlu perbaikan'}: {self._label(p)}"
        await self.repo.insert_many(p.organization_id, [p.leader], "REPORT_REVIEWED", title,
                                    note or p.title, plan_id)

    # ── Adendum saat berjalan & penutupan (PR3) ──────────────────────────────────────────────
    async def amendment_decided(self, plan_id: UUID | str, *, accepted: bool, note: str | None) -> None:
        p = await self._plan(plan_id)
        if accepted:
            title, body = f"Adendum {self._label(p)} siap ditandatangani", "PM sudah mengubah isi SK. Tinjau lalu terima adendum."
        else:
            title, body = f"Adendum {self._label(p)} ditolak", note or p.title
        await self.repo.insert_many(p.organization_id, [p.leader], "AMENDMENT_DECIDED", title, body, plan_id)

    async def amendment_accepted(self, plan_id: UUID | str) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm, *p.members], "AMENDMENT_ACCEPTED",
                                    f"Adendum {self._label(p)} berlaku", "Versi SK sebelumnya tidak berlaku lagi.", plan_id)

    async def completion_requested(self, plan_id: UUID | str) -> None:
        p = await self._plan(plan_id)
        await self.repo.insert_many(p.organization_id, [p.pm], "COMPLETION_REQUESTED",
                                    f"Pengajuan penutupan: {self._label(p)}", f"{p.title} — laporan akhir menunggu pemeriksaan.", plan_id)

    async def completion_decided(self, plan_id: UUID | str, *, approved: bool, note: str | None) -> None:
        p = await self._plan(plan_id)
        if approved:
            await self.repo.insert_many(p.organization_id, [p.leader, *p.members], "PLAN_COMPLETED",
                                        f"{self._label(p)} selesai", f"{p.title} — tim dan aset sudah dilepas.", plan_id)
        else:
            await self.repo.insert_many(p.organization_id, [p.leader], "COMPLETION_RETURNED",
                                        f"Laporan akhir {self._label(p)} perlu perbaikan", note or p.title, plan_id)
