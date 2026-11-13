"""SQL dokumen kendaraan dan pengemudi. Tanpa commit (batas transaksi di service); tanpa LIKE berawalan wildcard."""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.list_params import MAX_ROWS_UNPAGED
from app.core.repository import BaseRepository

_SELECT = """
    SELECT vd.vehicle_document_id, vd.vehicle_id, v.name AS vehicle_name, v.number_plate, vd.office_id,
           vd.doc_type_code, dt.nama AS doc_type_name, vd.doc_no, vd.issued_on, vd.expired_on,
           vd.file_object_id AS file_id, vd.status, vd.catatan, vd.create_at AS created_at,
           (vd.expired_on - CAST(:today AS date)) AS days_left
    FROM vehicle_document vd
    JOIN vehicle v ON v.vehicle_id = vd.vehicle_id
    JOIN document_type dt ON dt.code = vd.doc_type_code
"""


class VehicleDocumentRepository(BaseRepository):
    async def document_types(self) -> list[Any]:
        return list(await self.fetchall(
            "SELECT code, nama, berlaku_untuk, ambang_hari, harian_mulai_hari FROM document_type "
            "WHERE aktif ORDER BY berlaku_untuk, code"
        ))

    async def type_exists(self, code: str) -> bool:
        return await self.fetchone("SELECT code FROM document_type WHERE code = :c", {"c": code}) is not None

    async def type_for_vehicle(self, code: str) -> Any:
        return await self.fetchone(
            "SELECT code FROM document_type WHERE code = :c AND aktif AND berlaku_untuk = 'KENDARAAN'", {"c": code}
        )

    async def vehicle(self, vehicle_id: UUID) -> Any:
        """Kendaraan (kantor) bila ada; None bila tidak ada."""
        return await self.fetchone(
            "SELECT vehicle_id, office_id FROM vehicle WHERE vehicle_id = CAST(:v AS uuid) AND delete_at IS NULL",
            {"v": str(vehicle_id)},
        )

    async def file_office(self, file_id: UUID) -> UUID | None:
        office: UUID | None = await self.scalar(
            "SELECT office_id FROM file_object WHERE id = CAST(:f AS uuid)", {"f": str(file_id)})
        return office

    async def replace_active(self, vehicle_id: UUID, code: str) -> None:
        """Dokumen berlaku sejenis menjadi `replaced` (riwayat tetap ada) sebelum yang baru disisipkan."""
        await self.execute(
            "UPDATE vehicle_document SET status = 'replaced', update_at = now() "
            "WHERE vehicle_id = CAST(:v AS uuid) AND doc_type_code = :c AND status = 'active' AND delete_at IS NULL",
            {"v": str(vehicle_id), "c": code},
        )

    async def insert(self, office_id: UUID, vehicle_id: UUID, data: dict[str, Any]) -> UUID:
        new_id: UUID = await self.scalar(
            "INSERT INTO vehicle_document (office_id, vehicle_id, doc_type_code, doc_no, issued_on, expired_on, "
            "file_object_id, catatan) VALUES (CAST(:o AS uuid), CAST(:v AS uuid), :code, :no, :issued, :expired, "
            "CAST(:f AS uuid), :cat) RETURNING vehicle_document_id",
            {"o": str(office_id), "v": str(vehicle_id), "code": data["doc_type_code"], "no": data["doc_no"],
             "issued": data["issued_on"], "expired": data["expired_on"],
             "f": str(data["file_id"]) if data["file_id"] else None, "cat": data["catatan"]},
        )
        return new_id

    async def get(self, doc_id: UUID, today: date) -> Any:
        return await self.fetchone(
            _SELECT + " WHERE vd.vehicle_document_id = CAST(:id AS uuid) AND vd.delete_at IS NULL",
            {"id": str(doc_id), "today": today},
        )

    async def list_documents(
        self, today: date, offices: list[str] | None, vehicle_id: UUID | None, history: bool,
        due_within: int | None, driver_employee_id: str | None = None, doc_type_code: str | None = None,
    ) -> list[Any]:
        """Daftar dokumen. `offices` None = semua kantor. `due_within`: hanya yang jatuh tempo dalam N hari (atau
        sudah lewat). `driver_employee_id`: hanya kendaraan yang sedang dikemudikan karyawan itu."""
        return list(await self.fetchall(
            _SELECT + """
            WHERE vd.delete_at IS NULL AND v.delete_at IS NULL
              AND (CAST(:offices AS uuid[]) IS NULL OR vd.office_id = ANY(CAST(:offices AS uuid[])))
              AND (CAST(:vehicle AS uuid) IS NULL OR vd.vehicle_id = CAST(:vehicle AS uuid))
              AND (CAST(:dtc AS text) IS NULL OR vd.doc_type_code = CAST(:dtc AS text))
              AND (:history OR vd.status = 'active')
              AND (CAST(:due AS int) IS NULL OR vd.expired_on <= CAST(:today AS date) + CAST(:due AS int))
              AND (CAST(:drv AS uuid) IS NULL OR EXISTS (
                    SELECT 1 FROM vehicle_driver d WHERE d.vehicle_id = vd.vehicle_id
                    AND d.employee_id = CAST(:drv AS uuid) AND d.delete_at IS NULL
                    AND d.selesai_on IS NULL))
            ORDER BY vd.expired_on, vd.vehicle_id, vd.doc_type_code, vd.create_at DESC
            LIMIT :cap
            """,
            {"today": today, "offices": offices, "vehicle": str(vehicle_id) if vehicle_id else None,
             "history": history, "due": due_within, "drv": driver_employee_id,
             "dtc": doc_type_code, "cap": MAX_ROWS_UNPAGED},
        ))

    # -- pengemudi --
    async def drivers(self, vehicle_id: UUID) -> list[Any]:
        return list(await self.fetchall(
            "SELECT d.vehicle_driver_id, d.vehicle_id, d.employee_id, e.full_name AS employee_name, d.mulai_on, "
            "d.selesai_on FROM vehicle_driver d JOIN employee e ON e.employee_id = d.employee_id "
            "WHERE d.vehicle_id = CAST(:v AS uuid) AND d.delete_at IS NULL "
            "ORDER BY (d.selesai_on IS NULL) DESC, d.mulai_on DESC LIMIT :cap",
            {"v": str(vehicle_id), "cap": MAX_ROWS_UNPAGED},
        ))

    async def employee_office(self, employee_id: UUID) -> UUID | None:
        office: UUID | None = await self.scalar(
            "SELECT office_id FROM employee WHERE employee_id = CAST(:e AS uuid) AND delete_at IS NULL",
            {"e": str(employee_id)},
        )
        return office

    async def add_driver(self, office_id: UUID, vehicle_id: UUID, employee_id: UUID, today: date) -> UUID | None:
        """None bila karyawan itu sudah pengemudi aktif kendaraan ini (indeks unik parsial)."""
        new_id: UUID | None = await self.scalar(
            "INSERT INTO vehicle_driver (office_id, vehicle_id, employee_id, mulai_on) "
            "VALUES (CAST(:o AS uuid), CAST(:v AS uuid), CAST(:e AS uuid), CAST(:t AS date)) "
            "ON CONFLICT DO NOTHING RETURNING vehicle_driver_id",
            {"o": str(office_id), "v": str(vehicle_id), "e": str(employee_id), "t": today},
        )
        return new_id

    async def end_driver(self, vehicle_id: UUID, driver_id: UUID, today: date) -> bool:
        res = await self.execute(
            "UPDATE vehicle_driver SET selesai_on = GREATEST(mulai_on, CAST(:t AS date)), update_at = now() "
            "WHERE vehicle_driver_id = CAST(:d AS uuid) AND vehicle_id = CAST(:v AS uuid) "
            "AND selesai_on IS NULL AND delete_at IS NULL",
            {"d": str(driver_id), "v": str(vehicle_id), "t": today},
        )
        return bool(res.rowcount)
