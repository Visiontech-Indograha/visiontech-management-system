"""
app/services/plan_location_service.py
Titik lokasi penugasan SK (revisi PM 2026-09-26, dok 10). PM unit menetapkan titik koordinat &
radius absensi untuk SK draf maupun yang sedang berjalan. Teks lokasi di dokumen SK tidak diubah
(aturan 2: dokumen terbit tidak berubah) — yang berubah hanya titik geofence, tercatat di audit.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.guards import PlanAccess
from app.core.errors import AppError, ValidationError
from app.repositories.plan_location_repo import PlanLocationRepo

CLOSED = ("COMPLETED", "CANCELLED")
CLOSED_MESSAGE = "Titik lokasi tidak dapat diubah pada SK yang sudah selesai atau dibatalkan."
MIN_RADIUS, MAX_RADIUS = 10, 5000


class PlanLocationService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = PlanLocationRepo(db)

    async def location(self, access: PlanAccess) -> dict[str, Any] | None:
        site_id = access.plan.site_id
        if site_id is None:
            return None
        row = await self.repo.site(site_id, access.user.organization_id)
        return None if row is None else dict(row._mapping)

    async def set_location(self, access: PlanAccess, *, name: str, address: str | None,
                           lat: float, lng: float, radius_m: int) -> dict[str, Any]:
        plan = access.plan
        if plan.status in CLOSED:
            raise AppError("PLAN_CLOSED", CLOSED_MESSAGE, status=409)
        if not MIN_RADIUS <= radius_m <= MAX_RADIUS:
            raise ValidationError(f"Radius absensi harus {MIN_RADIUS}–{MAX_RADIUS} meter.")
        label = (" ".join(name.split()) or str(plan.location_text))[:190]
        org_id = access.user.organization_id
        # Titik yang sama disimpan lagi (nama + titik ≤ 5 m + radius sama) → pakai site yang ada,
        # agar daftar lokasi tidak menumpuk "Gudang Dumai (2)", "(3)", …
        same = await self.repo.same_site(org_id, label, lat, lng, radius_m)
        if same is not None:
            site_id = same.id
        else:
            # Titik/radius berubah → `site` baru (site lama tetap: riwayat absensi sah), padahal nama
            # unik per organisasi: nama yang sudah dipakai diberi nomor, mis. "Gudang Dumai (2)".
            taken = await self.repo.names_like(org_id, label)
            n = 2
            unique = label
            while unique in taken:
                unique, n = f"{label} ({n})", n + 1
            site_id = (await self.repo.create_site(org_id, unique, address, lat, lng, radius_m)).id
        await self.repo.set_plan_site(plan.id, site_id)
        row = await self.repo.site(site_id, org_id)
        return dict(row._mapping)
