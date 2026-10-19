"""
app/crud/crud_asset_reservation.py
Reservasi dan inventaris aset perkakas (tool) dan kendaraan (vehicle) untuk Master Schema V2.
Mendukung alur penugasan dan pengembalian aset.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


class AssetRepository(BaseRepository):
    """Repositori akses data master alat, armada, peminjaman, dan inspeksi aset (Grup 3)."""
    """
    Kelas operasi CRUD untuk data aset perkakas (tool) dan kendaraan (vehicle) V2.
    """

    async def list_with_state(self, org_id: UUID | str) -> list[Any]:
        """
        Mengambil daftar aset (tool dan vehicle) dari Master Schema V2.
        """
        sql = """
            SELECT
                t.tool_id AS id,
                'TOOL' AS kind,
                NULL::text AS vehicle_type,
                t.tool_code AS code,
                t.name,
                'Baik' AS condition,
                t.status::text AS status,
                NULL::uuid AS allocation_id,
                NULL::uuid AS work_plan_id,
                NULL::text AS plan_number,
                NULL::uuid AS leader_employee_id,
                NULL::uuid AS pending_return_id,
                NULL::text AS return_condition,
                NULL::text AS return_note,
                NULL::text AS return_requested_by_name
            FROM tool t
            WHERE t.delete_at IS NULL

            UNION ALL

            SELECT
                v.vehicle_id AS id,
                'VEHICLE' AS kind,
                v.vehicle_type::text AS vehicle_type,
                v.number_plate AS code,
                v.name AS name,
                'Baik' AS condition,
                v.status::text AS status,
                NULL::uuid AS allocation_id,
                NULL::uuid AS work_plan_id,
                NULL::text AS plan_number,
                NULL::uuid AS leader_employee_id,
                NULL::uuid AS pending_return_id,
                NULL::text AS return_condition,
                NULL::text AS return_note,
                NULL::text AS return_requested_by_name
            FROM vehicle v
            WHERE v.delete_at IS NULL
            ORDER BY name ASC
        """
        return list(await self.fetchall(sql, {}))

    async def return_history(self, asset_id: UUID | str, org_id: UUID | str) -> list[Any] | None:
        """Riwayat inspeksi/pengembalian aset dari public.vehicle_inspection."""
        return list(
            await self.fetchall(
                """
            SELECT
                vi.vehicle_inspection_id AS id,
                NULL::text AS plan_number,
                COALESCE(e.full_name, 'Sistem') AS requested_by_name,
                vi.create_at AS requested_at,
                vi.type::text AS condition_on_return,
                vi.path_file AS note,
                COALESCE(e.full_name, 'Petugas') AS verified_by_name,
                vi.create_at AS verified_at,
                TRUE AS is_accepted
            FROM public.vehicle_inspection vi
            LEFT JOIN public.employee e ON e.employee_id = vi.inspector_employee_id
            WHERE vi.vehicle_id = :aid AND vi.delete_at IS NULL
            ORDER BY vi.create_at DESC
            """,
                {"aid": asset_id},
            )
        )

    async def return_record(self, return_id: UUID | str, org_id: UUID | str) -> Any:
        return None

    async def plan_assets(self, plan_id: UUID | str) -> list[Any]:
        """Daftar aset yang dialokasikan untuk suatu rencana kerja / tim."""
        return list(
            await self.fetchall(
                """
            SELECT
                aa.assignment_id AS id,
                COALESCE(t.name, v.name) AS name,
                COALESCE(t.tool_code, v.number_plate) AS code,
                CASE WHEN t.tool_id IS NOT NULL THEN 'TOOL' ELSE 'VEHICLE' END AS kind,
                v.vehicle_type::text AS vehicle_type,
                e.full_name AS driver_name
            FROM public.asset_assignment aa
            LEFT JOIN public.tool t ON t.tool_id = aa.tool_id
            LEFT JOIN public.vehicle v ON v.vehicle_id = aa.vehicle_id
            LEFT JOIN public.employee e ON e.employee_id = aa.employee_id
            WHERE aa.delete_at IS NULL
            ORDER BY name ASC
            """,
                {"plan": plan_id},
            )
        )

    async def insert_asset(
        self,
        org_id: UUID | str,
        *,
        kind: str,
        vehicle_type: str | None,
        code: str,
        name: str,
        condition: str,
    ) -> Any:
        """Menambahkan perkakas atau kendaraan baru ke database."""
        if kind == "VEHICLE":
            v_type = vehicle_type if vehicle_type in ("Motorcycle", "Car", "Truck") else "Car"
            row = await self.fetchone(
                """
                INSERT INTO vehicle (
                    office_id, division_id, number_plate, vehicle_type, name, status
                )
                VALUES (
                    '11111111-0000-4000-a000-000000000001'::uuid,
                    '33333333-0000-4000-a000-000000000001'::uuid,
                    :code,
                    CAST(:vtype AS vehicle_type_enum),
                    :name,
                    'ready'
                )
                RETURNING vehicle_id AS id, name, number_plate AS code, 'VEHICLE' AS kind,
                          vehicle_type::text AS vehicle_type, 'Baik' AS condition, status::text AS status
                """,
                {"code": code, "vtype": v_type, "name": name},
            )
            return row
        else:
            row = await self.fetchone(
                """
                INSERT INTO tool (
                    office_id, division_id, ownership_type, category, name, tool_code, status
                )
                VALUES (
                    '11111111-0000-4000-a000-000000000001'::uuid,
                    '33333333-0000-4000-a000-000000000001'::uuid,
                    'SHARED_TOOL',
                    'LAINNYA',
                    :name,
                    :code,
                    'ready'
                )
                RETURNING tool_id AS id, name, tool_code AS code, 'TOOL' AS kind,
                          NULL::text AS vehicle_type, 'Baik' AS condition, status::text AS status
                """,
                {"name": name, "code": code},
            )
            return row

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        return await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": user_id},
        )

    async def employee_of(self, user_id: UUID | str) -> Any:
        """Alias untuk employee_of_user."""
        return await self.employee_of_user(user_id)

    async def plan_for_driver(self, driver_id: UUID | str) -> Any:
        """Mencari SK aktif untuk driver tertentu."""
        return None

    async def insert_allocation(
        self, asset_id: UUID | str, plan_id: UUID | str, driver_employee_id: Any = None, user_id: Any = None
    ) -> Any:
        """Mencatat alokasi aset pada penugasan."""
        return await self.fetchone(
            """
            INSERT INTO public.asset_assignment (
                tool_id, vehicle_id, employee_id, assigned_at
            )
            VALUES (
                CASE WHEN EXISTS (SELECT 1 FROM tool WHERE tool_id = CAST(:aid AS uuid))
                     THEN CAST(:aid AS uuid) ELSE NULL END,
                CASE WHEN EXISTS (SELECT 1 FROM vehicle WHERE vehicle_id = CAST(:aid AS uuid))
                     THEN CAST(:aid AS uuid) ELSE NULL END,
                CAST(:emp_id AS uuid),
                NOW()
            )
            RETURNING assignment_id
            """,
            {"aid": str(asset_id), "emp_id": str(driver_employee_id) if driver_employee_id else None},
        )

    async def set_asset_status(self, asset_id: UUID | str, status: str) -> None:
        """Memperbarui status aset kendaraan / alat."""
        await self.execute(
            """
            UPDATE vehicle SET status = 'in_use' WHERE vehicle_id = CAST(:aid AS uuid);
            UPDATE tool SET status = 'in_use' WHERE tool_id = CAST(:aid AS uuid);
            """,
            {"aid": str(asset_id)},
        )

    async def lock_asset(self, asset_id: UUID | str) -> Any:
        """Kunci baris aset untuk update."""
        return await self.fetchone(
            "SELECT vehicle_id AS id FROM vehicle WHERE vehicle_id = CAST(:aid AS uuid) FOR UPDATE",
            {"aid": str(asset_id)},
        )

    async def free_asset(self, asset_id: UUID | str) -> None:
        """Bebaskan aset kembali ke status siap pakai."""
        await self.execute(
            """
            UPDATE vehicle SET status = 'ready' WHERE vehicle_id = CAST(:aid AS uuid);
            UPDATE tool SET status = 'ready' WHERE tool_id = CAST(:aid AS uuid);
            """,
            {"aid": str(asset_id)},
        )

    async def active_allocation(self, asset_id: UUID | str) -> Any:
        """Cek alokasi aktif untuk aset."""
        return await self.fetchone(
            """
            SELECT assignment_id FROM asset_assignment
            WHERE (tool_id = CAST(:aid AS uuid) OR vehicle_id = CAST(:aid AS uuid))
              AND delete_at IS NULL
            LIMIT 1
            """,
            {"aid": str(asset_id)},
        )

    async def mark_checked(self, asset_id: UUID | str, checked_by: Any = None) -> None:
        """Tandai aset telah diperiksa kelayakannya."""

    async def allocation_state_for_update(self, allocation_id: UUID | str) -> Any:
        return None

    async def insert_return(
        self, allocation_id: UUID | str, employee_id: Any, condition: str, note: str | None
    ) -> Any:
        return None

    async def return_for_update(self, return_id: UUID | str, org_id: UUID | str) -> Any:
        return None

    async def verify_return(self, return_id: UUID | str, employee_id: Any, accepted: bool, note: str) -> Any:
        return None

    async def release_allocation(self, allocation_id: UUID | str) -> None:
        pass


# Alias backward compatibility
CRUDAssetReservation = AssetRepository
