"""
app/crud/crud_plan_location.py
Titik lokasi penugasan SK (revisi PM 2026-09-26). Setiap penetapan membuat baris `site` baru
lalu menautkannya ke SK — site lama tidak diubah agar riwayat absensi (jarak & radius saat itu)
tetap sah.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDPlanLocation(CRUDBase):
    """
    CRUD untuk mengelola titik lokasi (site) dari sebuah rencana kerja (SK).
    Memungkinkan pembuatan site baru untuk mempertahankan riwayat absensi.
    """

    async def site(self, site_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengambil informasi detail sebuah site/lokasi.

        Args:
            site_id (UUID | str): ID site.
            org_id (UUID | str): ID organisasi.

        Returns:
            Any: Record berisi detail site beserta latitude (lat) dan longitude (lng).
        """
        # Ekstrak titik koordinat (ST_Y untuk lat, ST_X untuk lng) dari kolom geometry postgis
        return await self.fetchone(
            """
            SELECT id, name, address, radius_m,
                   ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng
            FROM vms.site
            WHERE id = CAST(:id AS uuid) AND organization_id = CAST(:org AS uuid)
            """,
            {"id": site_id, "org": org_id})

    async def names_like(self, org_id: UUID | str, name: str) -> set[str]:
        """
        Mencari nama-nama lokasi (site) yang diawali dengan string tertentu.
        Digunakan untuk memastikan nama site unik per organisasi.

        Args:
            org_id (UUID | str): ID organisasi.
            name (str): Prefix nama yang dicari.

        Returns:
            set[str]: Himpunan nama-nama lokasi yang cocok.
        """
        # Mencari nama site yang bagian awalnya (left) sama dengan parameter name
        rows = await self.fetchall(
            """
            SELECT name FROM vms.site
            WHERE organization_id = CAST(:org AS uuid) AND left(name, char_length(:name)) = :name
            """,
            {"org": org_id, "name": name})
        return {r.name for r in rows}

    async def same_site(self, org_id: UUID | str, label: str, lat: float, lng: float,
                        radius_m: int) -> Any:
        """
        Mencari site yang memiliki label, titik koordinat (dalam radius 5 meter),
        dan radius yang sama untuk menghindari duplikasi site.

        Args:
            org_id (UUID | str): ID organisasi.
            label (str): Nama dasar site.
            lat (float): Garis lintang (latitude).
            lng (float): Garis bujur (longitude).
            radius_m (int): Radius absensi dalam meter.

        Returns:
            Any: Record ID site yang sama (jika ada).
        """
        # Cek apakah ada site dengan radius sama, nama mirip (label atau label (n)),
        # dan lokasinya berada dalam jarak 5 meter dari koordinat yang diberikan
        # (menggunakan ST_DWithin dari postgis).
        return await self.fetchone(
            """
            SELECT id FROM vms.site
            WHERE organization_id = CAST(:org AS uuid) AND radius_m = :radius
              AND (name = :name OR name LIKE :name || ' (%%)')
              AND ST_DWithin(location, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 5)
            ORDER BY char_length(name), name
            LIMIT 1
            """,
            {"org": org_id, "name": label, "radius": radius_m, "lat": lat, "lng": lng})

    async def create_site(self, org_id: UUID | str, name: str, address: str | None,
                          lat: float, lng: float, radius_m: int) -> Any:
        """
        Membuat record site/lokasi baru.

        Args:
            org_id (UUID | str): ID organisasi.
            name (str): Nama site.
            address (str | None): Alamat lengkap site.
            lat (float): Garis lintang (latitude).
            lng (float): Garis bujur (longitude).
            radius_m (int): Radius (meter).

        Returns:
            Any: Record ID dari site yang baru dibuat.
        """
        # Menyisipkan site baru dan membentuk tipe geography POINT (SRID 4326)
        # dari latitude dan longitude yang diberikan.
        return await self.fetchone(
            """
            INSERT INTO vms.site (organization_id, name, address, radius_m, location)
            VALUES (CAST(:org AS uuid), :name, :address, :radius,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
            RETURNING id
            """,
            {"org": org_id, "name": name, "address": address, "radius": radius_m, "lat": lat, "lng": lng})

    async def set_plan_site(self, plan_id: UUID | str, site_id: UUID | str) -> None:
        """
        Menetapkan atau memperbarui site yang digunakan oleh sebuah rencana kerja (SK).

        Args:
            plan_id (UUID | str): ID rencana kerja.
            site_id (UUID | str): ID lokasi (site).
        """
        # Memperbarui site_id pada tabel work_plan untuk menghubungkan SK dengan lokasi baru.
        await self.execute(
            """
            UPDATE vms.work_plan SET site_id = CAST(:site AS uuid)
            WHERE id = CAST(:plan AS uuid) AND deleted_at IS NULL
            """,
            {"plan": plan_id, "site": site_id})
