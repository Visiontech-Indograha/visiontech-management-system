"""
app/crud/crud_sync.py
Antrean luring (M12, dok 02 A-08): offline_operation + enqueue_offline_operation (db/01, db/02).
Idempoten per (user_id, client_op_id).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDSync(CRUDBase):
    """
    CRUD untuk mengelola antrean operasi luring (offline) yang dikirimkan oleh klien.
    Menjamin proses sinkronisasi data dari mode luring secara aman dan idempoten.
    """

    async def enqueue(self, org_id: UUID | str, user_id: UUID | str, device_id: str, client_op_id: UUID,
                      op_type: str, payload: dict[str, Any], client_created_at: datetime) -> Any:
        """
        Mencatat operasi luring ke dalam antrean atau menemukan operasi yang sudah ada.
        
        Args:
            org_id (UUID | str): ID organisasi.
            user_id (UUID | str): ID pengguna.
            device_id (str): ID perangkat yang melakukan sinkronisasi.
            client_op_id (UUID): ID unik operasi dari klien (menjamin idempotensi).
            op_type (str): Tipe operasi (misalnya INSERT, UPDATE).
            payload (dict[str, Any]): Data payload operasi.
            client_created_at (datetime): Waktu operasi dibuat di perangkat klien.
            
        Returns:
            Any: Record hasil enqueuing beserta status operasinya saat ini.
        """
        # Dua kueri terpisah digunakan di sini karena baris yang baru disisipkan di dalam 
        # fungsi basis data tidak terlihat oleh snapshot SELECT yang sama akibat aturan isolasi (MVCC).
        enqueued = await self.fetchone(
            """
            SELECT vms.enqueue_offline_operation(
                CAST(:org AS uuid), CAST(:user AS uuid), :device, CAST(:op AS uuid), :type,
                CAST(:payload AS jsonb), CAST(:created AS timestamptz)) AS id
            """,
            {"org": org_id, "user": user_id, "device": device_id, "op": client_op_id, "type": op_type,
             "payload": json.dumps(payload), "created": client_created_at})
        return await self.fetchone(
            """
            SELECT o.id, CAST(o.status AS text) AS status, o.error_message
            FROM vms.offline_operation o
            WHERE o.id = CAST(:id AS uuid)
            """,
            {"id": enqueued.id})

    async def mark(self, operation_id: UUID | str, status: str, error_message: str | None) -> None:
        """
        Menandai status akhir dari sebuah operasi luring setelah diproses.
        
        Args:
            operation_id (UUID | str): ID operasi luring.
            status (str): Status penyelesaian (misal: 'APPLIED', 'FAILED').
            error_message (str | None): Pesan error jika gagal, None jika berhasil.
        """
        # Memperbarui status operasi luring.
        # Jika statusnya 'APPLIED', maka applied_at akan disetel ke waktu sekarang (now()),
        # jika tidak, nilai applied_at tidak diubah.
        await self.execute(
            """
            UPDATE vms.offline_operation
               SET status = CAST(:status AS vms.sync_status), error_message = :error,
                   applied_at = CASE WHEN CAST(:status AS text) = 'APPLIED' THEN now() ELSE applied_at END
             WHERE id = :id
            """,
            {"id": operation_id, "status": status, "error": error_message})

    async def status_since(self, user_id: UUID | str, since: datetime | None) -> list[Any]:
        """
        Mengambil daftar status operasi luring pengguna yang diterima sejak waktu tertentu.
        
        Args:
            user_id (UUID | str): ID pengguna.
            since (datetime | None): Batas waktu pengambilan. Jika None, mengambil semua.
            
        Returns:
            list[Any]: Daftar maksimal 500 riwayat status operasi.
        """
        # Mengambil status operasi luring milik pengguna.
        # Jika parameter `since` diberikan, hanya mengambil operasi yang diterima (received_at)
        # setelah waktu tersebut untuk menghemat bandwidth sinkronisasi klien.
        return list(await self.fetchall(
            """
            SELECT CAST(client_op_id AS text) AS client_op_id, op_type, CAST(status AS text) AS status,
                   error_message, client_created_at, received_at, applied_at
            FROM vms.offline_operation
            WHERE user_id = :user
              AND (CAST(:since AS timestamptz) IS NULL OR received_at >= CAST(:since AS timestamptz))
            ORDER BY received_at DESC
            LIMIT 500
            """,
            {"user": user_id, "since": since}))
