"""
app/crud/crud_asset_reservation.py
Reservasi aset per SK (V-27) — padanan `domain.js` RESERVE_ASSET, RELEASE_ASSET, CHECK_ASSET.
Satu baris `asset_allocation` terbuka (released_at NULL) = aset sedang dipesan/dipakai SK itu.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDAssetReservation(CRUDBase):
    """
    Kelas operasi CRUD untuk menangani reservasi, alokasi, dan pengembalian aset.
    """

    async def list_with_state(self, org_id: UUID | str) -> list[Any]:
        """
        Mengambil daftar aset milik sebuah organisasi beserta status alokasi yang sedang berjalan
        dan pengajuan pengembalian yang masih menunggu persetujuan (R-19).
        
        Args:
            org_id (UUID | str): ID organisasi.
            
        Returns:
            list[Any]: Daftar aset dengan status alokasi dan pengembaliannya.
        """
        # Mengambil daftar aset dengan melakukan LEFT JOIN ke asset_allocation untuk alokasi aktif
        # dan LEFT JOIN LATERAL ke asset_return untuk mencari pengajuan pengembalian terakhir yang belum diverifikasi.
        return list(await self.fetchall(
            """
            SELECT a.id, a.organization_id, a.kind, a.vehicle_type, a.code, a.name, a.condition, a.status, al.id AS allocation_id, al.work_plan_id, wp.number AS plan_number,
                   wp.leader_employee_id, r.id AS pending_return_id, r.condition_on_return AS return_condition,
                   r.note AS return_note, re.full_name AS return_requested_by_name
            FROM vms.asset a
            LEFT JOIN vms.asset_allocation al ON al.asset_id = a.id AND al.released_at IS NULL
            LEFT JOIN vms.work_plan wp ON wp.id = al.work_plan_id
            LEFT JOIN LATERAL (SELECT id, condition_on_return, note, requested_by FROM vms.asset_return x
                               WHERE x.asset_allocation_id = al.id AND x.verified_at IS NULL
                               ORDER BY x.requested_at DESC LIMIT 1) r ON true
            LEFT JOIN vms.employee re ON re.id = r.requested_by
            WHERE a.organization_id = :org AND a.deleted_at IS NULL
            ORDER BY a.name
            """,
            {"org": org_id}))

    _RETURN_ROWS = """
        SELECT r.id, r.requested_at, r.verified_at, r.condition_on_return, r.note, r.is_accepted,
               rq.full_name AS requested_by_name, vf.full_name AS verified_by_name,
               wp.number AS plan_number, wp.title AS plan_title, al.allocated_at, dr.full_name AS driver_name,
               a.id AS asset_id, a.name AS asset_name, a.code AS asset_code, CAST(a.kind AS text) AS asset_kind,
               a.vehicle_type
        FROM vms.asset_return r
        JOIN vms.asset_allocation al ON al.id = r.asset_allocation_id
        JOIN vms.asset a ON a.id = al.asset_id
        JOIN vms.work_plan wp ON wp.id = al.work_plan_id
        JOIN vms.employee rq ON rq.id = r.requested_by
        LEFT JOIN vms.employee vf ON vf.id = r.verified_by
        LEFT JOIN vms.employee dr ON dr.id = al.driver_employee_id
    """

    async def return_history(self, asset_id: UUID | str, org_id: UUID | str) -> list[Any] | None:
        """
        Mengambil riwayat pengembalian sebuah aset, diurutkan dari yang terbaru.
        Mengembalikan None jika aset tidak ditemukan atau bukan milik organisasi ini.
        
        Args:
            asset_id (UUID | str): ID aset.
            org_id (UUID | str): ID organisasi.
            
        Returns:
            list[Any] | None: Daftar riwayat pengembalian, atau None jika aset tidak valid.
        """
        # Memastikan bahwa aset tersebut benar-benar ada dan milik organisasi yang diberikan
        if not await self.scalar("SELECT 1 FROM vms.asset WHERE id = :id AND organization_id = :org",
                                 {"id": asset_id, "org": org_id}):
            return None
            
        # Mengambil riwayat pengembalian untuk aset tersebut, diurutkan berdasarkan waktu permintaan secara menurun (descending)
        return list(await self.fetchall(self._RETURN_ROWS + " WHERE a.id = :id ORDER BY r.requested_at DESC",
                                        {"id": asset_id}))

    async def return_record(self, return_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengambil detail satu catatan pengembalian spesifik jika asetnya milik organisasi.
        
        Args:
            return_id (UUID | str): ID pengembalian aset.
            org_id (UUID | str): ID organisasi.
            
        Returns:
            Any: Data catatan pengembalian, atau None jika tidak ditemukan.
        """
        # Mengambil satu baris spesifik data pengembalian berdasarkan ID, dan memvalidasi organisasi dari aset terkait
        return await self.fetchone(self._RETURN_ROWS + " WHERE r.id = :id AND a.organization_id = :org",
                                   {"id": return_id, "org": org_id})

    async def plan_assets(self, plan_id: UUID | str) -> list[Any]:
        """
        Mengambil daftar aset yang pernah atau sedang dialokasikan ke suatu Surat Kerja (SK),
        beserta status pengembalian terakhirnya untuk keperluan mode presentasi.
        
        Args:
            plan_id (UUID | str): ID Surat Kerja (work plan).
            
        Returns:
            list[Any]: Daftar aset terkait SK.
        """
        # Mengambil alokasi aset untuk suatu SK, di-JOIN dengan aset dan pengemudi. 
        # Menggunakan LEFT JOIN LATERAL untuk mengambil informasi pengembalian terbaru (kondisi dan status penerimaan).
        return list(await self.fetchall(
            """
            SELECT a.id, a.name, a.code, CAST(a.kind AS text) AS kind, a.vehicle_type, dr.full_name AS driver_name,
                   al.allocated_at, al.released_at, r.condition_on_return AS returned_condition,
                   r.is_accepted AS return_accepted, al.id AS allocation_id, CAST(a.status AS text) AS asset_status
            FROM vms.asset_allocation al
            JOIN vms.asset a ON a.id = al.asset_id
            LEFT JOIN vms.employee dr ON dr.id = al.driver_employee_id
            LEFT JOIN LATERAL (SELECT x.condition_on_return, x.is_accepted FROM vms.asset_return x
                               WHERE x.asset_allocation_id = al.id ORDER BY x.requested_at DESC LIMIT 1) r ON true
            WHERE al.work_plan_id = :plan
            ORDER BY al.allocated_at
            """,
            {"plan": plan_id}))

    async def lock_asset(self, asset_id: UUID | str) -> Any:
        """
        Mengunci baris aset di database untuk proses pembaruan (FOR UPDATE)
        sehingga mencegah race condition.
        
        Args:
            asset_id (UUID | str): ID aset.
            
        Returns:
            Any: Data aset yang terkunci.
        """
        # Melakukan SELECT ... FOR UPDATE untuk mengunci baris aset agar transaksi lain tidak dapat mengubahnya secara bersamaan
        return await self.fetchone(
            """
            SELECT id, CAST(kind AS text) AS kind, CAST(status AS text) AS status
            FROM vms.asset WHERE id = :id AND deleted_at IS NULL
            FOR UPDATE
            """,
            {"id": asset_id},
        )

    async def plan_for_driver(self, plan_id: UUID | str, driver_id: UUID | str | None) -> Any:
        """
        Mengecek status Surat Kerja dan memvalidasi apakah seorang pengemudi 
        merupakan bagian dari tim penugasan tersebut (termasuk sebagai ketua).
        
        Args:
            plan_id (UUID | str): ID Surat Kerja.
            driver_id (UUID | str | None): ID karyawan pengemudi.
            
        Returns:
            Any: Status SK dan flag boolean driver_on_team.
        """
        # Memeriksa status Surat Kerja (SK) dan menggunakan fungsi EXISTS untuk memvalidasi
        # apakah pengemudi adalah ketua tim (leader) atau anggota tim yang valid (masa berlakunya mencakup periode tak terhingga).
        return await self.fetchone(
            """
            SELECT CAST(wp.status AS text) AS status,
                   wp.leader_employee_id = CAST(:driver AS uuid) OR EXISTS (
                       SELECT 1 FROM vms.work_plan_member m
                        WHERE m.work_plan_id = wp.id AND m.employee_id = CAST(:driver AS uuid)
                          AND upper_inf(m.valid_period)) AS driver_on_team
            FROM vms.work_plan wp WHERE wp.id = :plan
            """,
            {"plan": plan_id, "driver": driver_id},
        )

    async def active_allocation(self, asset_id: UUID | str) -> Any:
        """
        Mencari data alokasi yang sedang aktif (belum dirilis/dikembalikan) untuk suatu aset.
        
        Args:
            asset_id (UUID | str): ID aset.
            
        Returns:
            Any: Data alokasi aktif beserta status SK terkait.
        """
        # Mengambil record alokasi yang 'released_at'-nya NULL (berarti masih dipakai) beserta status SK
        return await self.fetchone(
            """
            SELECT al.id, al.work_plan_id, al.driver_employee_id, al.driver_checked_at,
                   CAST(wp.status AS text) AS plan_status
            FROM vms.asset_allocation al JOIN vms.work_plan wp ON wp.id = al.work_plan_id
            WHERE al.asset_id = :asset AND al.released_at IS NULL
            """,
            {"asset": asset_id},
        )

    async def insert_allocation(self, asset_id: UUID | str, plan_id: UUID | str, driver_id: UUID | str | None,
                                user_id: UUID | str) -> Any:
        """
        Membuat alokasi aset baru untuk sebuah Surat Kerja.
        
        Args:
            asset_id (UUID | str): ID aset.
            plan_id (UUID | str): ID Surat Kerja.
            driver_id (UUID | str | None): ID karyawan pengemudi (jika ada).
            user_id (UUID | str): ID pengguna yang melakukan alokasi.
            
        Returns:
            Any: Record alokasi yang baru dibuat.
        """
        # Menyisipkan baris baru ke tabel asset_allocation.
        # Kolom allocated_by diambil dengan subquery dari tabel app_user berdasarkan user_id.
        return await self.fetchone(
            """
            INSERT INTO vms.asset_allocation (asset_id, work_plan_id, driver_employee_id, allocated_by)
            VALUES (:asset, :plan, :driver, (SELECT employee_id FROM vms.app_user WHERE id = :uid))
            RETURNING id, asset_id, work_plan_id, driver_employee_id, allocated_by, allocated_at, released_at
            """,
            {"asset": asset_id, "plan": plan_id, "driver": driver_id, "uid": user_id},
        )

    async def set_asset_status(self, asset_id: UUID | str, status: str) -> None:
        """
        Memperbarui status sebuah aset (misalnya menjadi ALLOCATED, MAINTENANCE, dll).
        
        Args:
            asset_id (UUID | str): ID aset.
            status (str): Status aset yang baru.
        """
        # Memperbarui nilai 'status' dari aset tertentu
        await self.execute(
            "UPDATE vms.asset SET status = CAST(:status AS vms.asset_status), updated_at = now() WHERE id = :id",
            {"id": asset_id, "status": status})

    async def free_asset(self, asset_id: UUID | str, allocation_id: UUID | str, condition: str | None) -> None:
        """
        Menutup reservasi/alokasi sehingga aset tersedia kembali. 
        Mencatat kondisi akhir aset jika diberikan saat pengembalian (banding).
        (Mewakili operasi domain.js freeAsset)
        
        Args:
            asset_id (UUID | str): ID aset.
            allocation_id (UUID | str): ID alokasi yang ingin ditutup.
            condition (str | None): Kondisi aset saat dikembalikan.
        """
        # Memperbarui alokasi dengan mengatur waktu rilis ke saat ini
        await self.execute("UPDATE vms.asset_allocation SET released_at = now() WHERE id = :id",
                           {"id": allocation_id})
        # Memperbarui aset: mengembalikan status ke 'AVAILABLE' dan mencatat kondisinya jika diberikan
        await self.execute(
            """
            UPDATE vms.asset SET status = 'AVAILABLE', condition = COALESCE(:condition, condition), updated_at = now()
             WHERE id = :id
            """,
            {"id": asset_id, "condition": condition})

    async def mark_checked(self, allocation_id: UUID | str) -> None:
        """
        Menandai bahwa aset telah diperiksa oleh pengemudi.
        
        Args:
            allocation_id (UUID | str): ID alokasi.
        """
        # Memperbarui kolom driver_checked_at menjadi waktu saat ini untuk mencatat inspeksi oleh pengemudi
        await self.execute("UPDATE vms.asset_allocation SET driver_checked_at = now() WHERE id = :id",
                           {"id": allocation_id})

    async def employee_of(self, user_id: UUID | str) -> str | None:
        """
        Mendapatkan ID karyawan yang terkait dengan seorang pengguna (app_user).
        
        Args:
            user_id (UUID | str): ID pengguna.
            
        Returns:
            str | None: ID karyawan, atau None jika pengguna tidak memiliki karyawan terkait.
        """
        # Mengambil nilai tunggal employee_id (sebagai string) dari pengguna yang sesuai
        employee: str | None = await self.scalar(
            "SELECT CAST(employee_id AS text) FROM vms.app_user WHERE id = :uid", {"uid": user_id})
        return employee

