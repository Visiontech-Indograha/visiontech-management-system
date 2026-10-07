"""
app/crud/crud_document.py
Dokumen pribadi karyawan — seluruh kueri modul (antrean HR R-19; daftar/ajukan/verifikasi R-20).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDDocument(CRUDBase):
    """
    Kelas operasi CRUD untuk menangani dokumen pribadi karyawan,
    seperti antrean verifikasi HR (R-19), pengajuan, dan riwayat dokumen (R-20).
    """

    async def pending_for_org(self, org_id: UUID | str, user_id: UUID | str) -> list[Any]:
        """
        Mendapatkan daftar dokumen dengan status 'PENDING' (menunggu verifikasi)
        yang dimiliki oleh karyawan di sebuah organisasi. Diurutkan dari yang paling lama.

        Args:
            org_id (UUID | str): ID organisasi.
            user_id (UUID | str): ID pengguna saat ini.

        Returns:
            list[Any]: Daftar dokumen yang menunggu diverifikasi HR.
        """
        # Mengambil dokumen berstatus PENDING dengan JOIN ke tabel employee untuk memvalidasi organisasi.
        # Kolom uploaded_by_me menunjukkan apakah dokumen diunggah oleh pengguna ini.
        return list(await self.fetchall(
            """
            SELECT d.id, d.employee_id, e.full_name, d.doc_type, d.number_masked, d.expiry_date, d.file_id,
                   d.created_at AS uploaded_at, (d.uploaded_by = CAST(:uid AS uuid)) AS uploaded_by_me
            FROM vms.employee_document d JOIN vms.employee e ON e.id = d.employee_id
            WHERE e.organization_id = :org AND e.deleted_at IS NULL AND d.status = 'PENDING'
            ORDER BY d.created_at
            """,
            {"org": org_id, "uid": user_id}))

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        """
        Mendapatkan ID karyawan yang dikaitkan dengan sebuah akun pengguna.

        Args:
            user_id (UUID | str): ID pengguna.

        Returns:
            Any: ID karyawan.
        """
        # Mengambil atribut employee_id dari pengguna aplikasi
        return await self.scalar("SELECT employee_id FROM vms.app_user WHERE id = CAST(:uid AS uuid)", {"uid": user_id})

    async def employee_in_org(self, emp_id: UUID | str, org_id: UUID | str) -> bool:
        """
        Memeriksa apakah seorang karyawan merupakan bagian dari organisasi tertentu.

        Args:
            emp_id (UUID | str): ID karyawan.
            org_id (UUID | str): ID organisasi.

        Returns:
            bool: True jika karyawan berada di organisasi tersebut.
        """
        # Mengecek keberadaan karyawan (EXISTS) di dalam organisasi
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.employee WHERE id = CAST(:emp AS uuid) AND organization_id = :org)",
            {"emp": emp_id, "org": org_id}))

    async def list_for_employee(self, emp_id: UUID | str) -> list[Any]:
        """
        Mengambil semua riwayat dokumen pribadi untuk seorang karyawan,
        diurutkan dari yang terbaru.

        Args:
            emp_id (UUID | str): ID karyawan.

        Returns:
            list[Any]: Daftar dokumen karyawan.
        """
        # Mengambil semua baris data dari vms.employee_document untuk karyawan terkait
        return list(await self.fetchall(
            """
            SELECT id, employee_id, doc_type, number_masked, expiry_date, status, lifecycle, file_id,
                   uploaded_by, verified_by, verified_at, review_note, created_at
            FROM vms.employee_document WHERE employee_id = CAST(:emp AS uuid)
            ORDER BY created_at DESC
            """,
            {"emp": emp_id}))

    async def has_pending(self, emp_id: UUID | str, doc_type: str) -> bool:
        """
        Memeriksa apakah ada dokumen dengan tipe tertentu yang masih berstatus 'PENDING'
        untuk karyawan tersebut (mencegah pengajuan ganda).

        Args:
            emp_id (UUID | str): ID karyawan.
            doc_type (str): Tipe dokumen (misal: 'KTP', 'SIM').

        Returns:
            bool: True jika ada pengajuan yang tertunda.
        """
        # Mengecek apakah (EXISTS) ada dokumen untuk karyawan ini dengan status 'PENDING' di tipe yang sama
        return bool(await self.scalar(
            """SELECT EXISTS (SELECT 1 FROM vms.employee_document
                              WHERE employee_id = CAST(:emp AS uuid) AND doc_type = :type AND status = 'PENDING')""",
            {"emp": emp_id, "type": doc_type}))

    async def belongs_to(self, doc_id: UUID | str, emp_id: UUID | str) -> bool:
        """
        Memeriksa apakah sebuah dokumen benar-benar milik karyawan tertentu.

        Args:
            doc_id (UUID | str): ID dokumen.
            emp_id (UUID | str): ID karyawan.

        Returns:
            bool: True jika dokumen milik karyawan.
        """
        # Mengecek keberadaan (EXISTS) dokumen berdasarkan ID dokumen dan ID karyawan
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.employee_document WHERE id = CAST(:id AS uuid) AND employee_id = CAST(:emp AS uuid))",
            {"id": doc_id, "emp": emp_id}))

    async def insert(self, *, emp_id: UUID | str, doc_type: str, masked: str, number_hash: bytes,
                     expiry: Any, file_id: UUID | str, user_id: UUID | str, supersedes_id: UUID | str | None) -> Any:
        """
        Menambahkan (menyisipkan) rekaman pengajuan dokumen karyawan yang baru.

        Args:
            emp_id (UUID | str): ID karyawan.
            doc_type (str): Tipe dokumen.
            masked (str): Nomor dokumen yang disamarkan (misal "1234xxxx").
            number_hash (bytes): Hash SHA256 dari nomor dokumen.
            expiry (Any): Tanggal kedaluwarsa.
            file_id (UUID | str): ID file lampiran dari dokumen.
            user_id (UUID | str): ID pengguna yang mengunggah.
            supersedes_id (UUID | str | None): ID dokumen lama yang digantikan (jika ada).

        Returns:
            Any: Baris data dokumen yang baru dibuat.
        """
        # Menyisipkan data ke dalam tabel employee_document dan mengembalikan baris datanya
        return await self.fetchone(
            """
            INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, number_sha256,
                                               expiry_date, file_id, uploaded_by, supersedes_id)
            VALUES (CAST(:emp AS uuid), :type, :masked, :hash, :expiry, CAST(:fid AS uuid), CAST(:uid AS uuid),
                    CAST(:super_id AS uuid))
            RETURNING id, employee_id, doc_type, number_masked, expiry_date, status, lifecycle, file_id,
                      uploaded_by, verified_by, verified_at, review_note, created_at
            """,
            {"emp": emp_id, "type": doc_type, "masked": masked, "hash": number_hash, "expiry": expiry,
             "fid": file_id, "uid": user_id, "super_id": supersedes_id})

    async def for_decision(self, doc_id: UUID | str, emp_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengambil data dokumen dan menguncinya untuk proses pengambilan keputusan verifikasi (FOR UPDATE).
        Hanya mengembalikan data jika dokumen tersebut milik karyawan dari organisasi yang sesuai.
        (Mencegah dua pemeriksa mengambil keputusan di waktu yang bersamaan).

        Args:
            doc_id (UUID | str): ID dokumen.
            emp_id (UUID | str): ID karyawan.
            org_id (UUID | str): ID organisasi.

        Returns:
            Any: Baris data dokumen yang dikunci.
        """
        # Melakukan SELECT ... FOR UPDATE OF d untuk mengunci baris spesifik di tabel employee_document,
        # setelah di-JOIN dengan employee untuk validasi org_id.
        return await self.fetchone(
            """
            SELECT d.id, d.doc_type, d.status::text AS status, d.uploaded_by
            FROM vms.employee_document d JOIN vms.employee e ON e.id = d.employee_id
            WHERE d.id = CAST(:id AS uuid) AND d.employee_id = CAST(:emp AS uuid) AND e.organization_id = :org
            FOR UPDATE OF d
            """,
            {"id": doc_id, "emp": emp_id, "org": org_id})

    async def supersede_current(self, emp_id: UUID | str, doc_id: UUID | str, doc_type: str) -> None:
        """
        Mengubah status siklus hidup dokumen (lifecycle) dokumen-dokumen yang lama (CURRENT)
        menjadi digantikan (SUPERSEDED) saat dokumen baru dengan tipe yang sama telah aktif.

        Args:
            emp_id (UUID | str): ID karyawan.
            doc_id (UUID | str): ID dokumen baru yang menjadi CURRENT.
            doc_type (str): Tipe dokumen.
        """
        # Mengatur lifecycle menjadi SUPERSEDED untuk dokumen yang bukan dokumen baru ini (id <> baru)
        await self.execute(
            """
            UPDATE vms.employee_document SET lifecycle = 'SUPERSEDED'
            WHERE employee_id = CAST(:emp AS uuid) AND lifecycle = 'CURRENT' AND id <> CAST(:id AS uuid)
              AND doc_type = :type
            """,
            {"emp": emp_id, "id": doc_id, "type": doc_type})

    async def decide(self, doc_id: UUID | str, *, status: str, lifecycle: str, user_id: UUID | str,
                     note: str | None) -> Any:
        """
        Menyimpan hasil keputusan (verifikasi) terhadap pengajuan dokumen.
        (Misalnya mengubah status menjadi 'APPROVED' atau 'REJECTED' dan lifecycle-nya).

        Args:
            doc_id (UUID | str): ID dokumen.
            status (str): Status verifikasi (APPROVED/REJECTED).
            lifecycle (str): Siklus hidup dokumen (CURRENT, ARCHIVED, dll).
            user_id (UUID | str): ID HR yang memverifikasi.
            note (str | None): Catatan tambahan verifikasi.

        Returns:
            Any: Baris data dokumen yang telah diperbarui.
        """
        # Memperbarui data dokumen: status, lifecycle, serta merekam siapa yang memverifikasi, waktu verifikasi, dan catatannya.
        return await self.fetchone(
            """
            UPDATE vms.employee_document
            SET status = CAST(:status AS vms.personal_document_status),
                lifecycle = CAST(:lifecycle AS vms.personal_document_lifecycle),
                verified_by = CAST(:uid AS uuid), verified_at = now(), review_note = :note
            WHERE id = CAST(:id AS uuid)
            RETURNING id, employee_id, doc_type, number_masked, expiry_date, status, lifecycle, file_id,
                      uploaded_by, verified_by, verified_at, review_note, created_at
            """,
            {"id": doc_id, "status": status, "lifecycle": lifecycle, "uid": user_id, "note": note})
