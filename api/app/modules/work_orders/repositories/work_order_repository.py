"""
app/modules/work_orders/repositories/work_order_repository.py

Repositori SQL untuk 4 Pilar Tabel Kerja VMS V2:
1. client_work_orders
2. work_order_surveys
3. work_order_survey_points
4. work_order_items
5. work_order_bom
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository, escape_like
from app.core.time import utcnow


class WorkOrderRepository(BaseRepository):
    """Akses data basis data PostgreSQL untuk alur kerja terpadu Work Orders."""

    async def generate_wo_number(self) -> str:
        """Menghasilkan nomor WO otomatis unik berbasis tahun-bulan: WO-YYYYMM-XXXX."""
        now = utcnow()
        prefix = f"WO-{now.strftime('%Y%m')}-"
        row = await self.fetchone(
            """
            SELECT wo_number FROM client_work_orders
            WHERE wo_number LIKE :pfx || '%'
            ORDER BY create_at DESC LIMIT 1
            """,
            {"pfx": prefix},
        )
        if not row or not row.wo_number:
            return f"{prefix}0001"
        try:
            seq = int(row.wo_number.split("-")[-1]) + 1
            return f"{prefix}{seq:04d}"
        except (ValueError, IndexError):
            return f"{prefix}0001"

    async def list_work_orders(
        self,
        *,
        division_id: UUID | None = None,
        status: str | None = None,
        client_id: UUID | None = None,
        pm_id: UUID | None = None,
        lead_team_id: UUID | None = None,
        q: str | None = None,
        limit: int = 50,
    ) -> Sequence[Any]:
        sql = """
            SELECT
                wo.work_order_id,
                wo.wo_number,
                wo.client_id,
                c.name AS client_name,
                wo.client_site_id,
                cs.site_name,
                cs.address AS site_address,
                cs.latitude AS site_lat,
                cs.longitude AS site_lng,
                wo.division_id,
                d.name AS division_name,
                wo.pm_id,
                e.full_name AS pm_name,
                e.office_id AS pm_office_id,
                wo.lead_team_id,
                t.name AS team_name,
                wo.title,
                wo.initial_complaint,
                wo.status,
                wo.survey_assigned_at,
                wo.survey_submitted_at,
                wo.survey_approved_at,
                wo.bast_signed_at,
                wo.bast_signer_name,
                (SELECT COUNT(*)::int FROM work_order_items woi
                 WHERE woi.work_order_id = wo.work_order_id AND woi.delete_at IS NULL) AS total_items,
                (SELECT COUNT(*)::int FROM work_order_items woi
                 WHERE woi.work_order_id = wo.work_order_id AND woi.status = 'DONE' AND woi.delete_at IS NULL
                ) AS completed_items,
                wo.create_at AS created_at
            FROM client_work_orders wo
            LEFT JOIN client c ON c.client_id = wo.client_id AND c.delete_at IS NULL
            LEFT JOIN client_sites cs ON cs.site_id = wo.client_site_id AND cs.delete_at IS NULL
            LEFT JOIN division d ON d.division_id = wo.division_id AND d.delete_at IS NULL
            LEFT JOIN employee e ON e.employee_id = wo.pm_id AND e.delete_at IS NULL
            LEFT JOIN team t ON t.team_id = wo.lead_team_id AND t.delete_at IS NULL
            WHERE wo.delete_at IS NULL
        """
        params: dict[str, Any] = {"limit": limit}
        if division_id:
            sql += " AND wo.division_id = CAST(:div_id AS uuid)"
            params["div_id"] = str(division_id)
        if status:
            sql += " AND wo.status = :status"
            params["status"] = status
        if client_id:
            sql += " AND wo.client_id = CAST(:client_id AS uuid)"
            params["client_id"] = str(client_id)
        if pm_id:
            sql += " AND wo.pm_id = CAST(:pm_id AS uuid)"
            params["pm_id"] = str(pm_id)
        if lead_team_id:
            sql += " AND wo.lead_team_id = CAST(:lead_team_id AS uuid)"
            params["lead_team_id"] = str(lead_team_id)
        if q:
            sql += (
                " AND (wo.wo_number ILIKE '%' || :q || '%'"
                " OR wo.title ILIKE '%' || :q || '%'"
                " OR c.name ILIKE '%' || :q || '%')"
            )
            params["q"] = escape_like(q)

        sql += " ORDER BY wo.create_at DESC LIMIT :limit"
        return await self.fetchall(sql, params)

    async def get_work_order(self, work_order_id: UUID | str) -> Any:
        sql = """
            SELECT
                wo.work_order_id,
                wo.wo_number,
                wo.client_id,
                c.name AS client_name,
                wo.client_site_id,
                cs.site_name,
                cs.address AS site_address,
                cs.latitude AS site_lat,
                cs.longitude AS site_lng,
                wo.division_id,
                d.name AS division_name,
                wo.pm_id,
                e.full_name AS pm_name,
                e.office_id AS pm_office_id,
                wo.lead_team_id,
                t.name AS team_name,
                wo.title,
                wo.initial_complaint,
                wo.status,
                wo.survey_assigned_at,
                wo.survey_submitted_at,
                wo.survey_approved_at,
                wo.bast_signed_at,
                wo.bast_signer_name,
                (SELECT COUNT(*)::int FROM work_order_items woi
                 WHERE woi.work_order_id = wo.work_order_id AND woi.delete_at IS NULL) AS total_items,
                (SELECT COUNT(*)::int FROM work_order_items woi
                 WHERE woi.work_order_id = wo.work_order_id AND woi.status = 'DONE' AND woi.delete_at IS NULL
                ) AS completed_items,
                wo.create_at AS created_at
            FROM client_work_orders wo
            LEFT JOIN client c ON c.client_id = wo.client_id AND c.delete_at IS NULL
            LEFT JOIN client_sites cs ON cs.site_id = wo.client_site_id AND cs.delete_at IS NULL
            LEFT JOIN division d ON d.division_id = wo.division_id AND d.delete_at IS NULL
            LEFT JOIN employee e ON e.employee_id = wo.pm_id AND e.delete_at IS NULL
            LEFT JOIN team t ON t.team_id = wo.lead_team_id AND t.delete_at IS NULL
            WHERE wo.work_order_id = CAST(:id AS uuid) AND wo.delete_at IS NULL
        """
        return await self.fetchone(sql, {"id": str(work_order_id)})

    async def create_work_order(self, data: dict[str, Any]) -> str:
        sql = """
            INSERT INTO client_work_orders (
                wo_number, client_id, client_site_id, division_id,
                pm_id, lead_team_id, title, initial_complaint, status
            ) VALUES (
                :wo_number, CAST(:client_id AS uuid),
                CAST(:client_site_id AS uuid),
                CAST(:division_id AS uuid), CAST(:pm_id AS uuid),
                CAST(:lead_team_id AS uuid),
                :title, :initial_complaint, 'WAITING_SURVEY'
            ) RETURNING work_order_id
        """
        wo_id = await self.scalar(sql, data)
        return str(wo_id)

    async def assign_survey(
        self, work_order_id: UUID | str, lead_team_id: UUID | str, survey_date: date | None, notes: str | None
    ) -> None:
        await self.execute(
            """
            UPDATE client_work_orders
            SET lead_team_id = CAST(:team_id AS uuid),
                status = 'SURVEY_IN_PROGRESS',
                survey_assigned_at = NOW(),
                update_at = NOW()
            WHERE work_order_id = CAST(:wo_id AS uuid) AND delete_at IS NULL
            """,
            {"wo_id": str(work_order_id), "team_id": str(lead_team_id)},
        )
        # Buat atau update draft work_order_surveys
        existing_survey = await self.scalar(
            "SELECT survey_id FROM work_order_surveys WHERE work_order_id = CAST(:wo_id AS uuid) AND delete_at IS NULL",
            {"wo_id": str(work_order_id)},
        )
        if not existing_survey:
            await self.execute(
                """
                INSERT INTO work_order_surveys (
                    work_order_id, surveyor_team_id, survey_date, narrative, status
                ) VALUES (
                    CAST(:wo_id AS uuid), CAST(:team_id AS uuid),
                    COALESCE(CAST(:sdate AS date), CURRENT_DATE), :notes, 'DRAFT'
                )
                """,
                {
                    "wo_id": str(work_order_id),
                    "team_id": str(lead_team_id),
                    "sdate": survey_date,
                    "notes": notes,
                },
            )

    async def submit_survey(
        self,
        work_order_id: UUID | str,
        surveyor_team_id: UUID | str | None,
        narrative: str | None,
        format_type: str,
        points: list[dict[str, Any]],
        general_bom: list[dict[str, Any]],
    ) -> None:
        # 1. Update atau insert work_order_surveys
        survey_id = await self.scalar(
            "SELECT survey_id FROM work_order_surveys WHERE work_order_id = CAST(:wo_id AS uuid) AND delete_at IS NULL",
            {"wo_id": str(work_order_id)},
        )
        if survey_id:
            await self.execute(
                """
                UPDATE work_order_surveys
                SET narrative = :narrative,
                    format = :format,
                    general_bom = CAST(:gbom AS jsonb),
                    status = 'SUBMITTED',
                    submitted_at = NOW(),
                    update_at = NOW()
                WHERE survey_id = CAST(:sid AS uuid)
                """,
                {
                    "sid": str(survey_id),
                    "narrative": narrative,
                    "format": format_type,
                    "gbom": json.dumps(general_bom),
                },
            )
        else:
            survey_id = await self.scalar(
                """
                INSERT INTO work_order_surveys (
                    work_order_id, surveyor_team_id, survey_date, narrative,
                    format, general_bom, status, submitted_at
                ) VALUES (
                    CAST(:wo_id AS uuid),
                    CAST(:tid AS uuid),
                    CURRENT_DATE, :narrative, :format,
                    CAST(:gbom AS jsonb), 'SUBMITTED', NOW()
                ) RETURNING survey_id
                """,
                {
                    "wo_id": str(work_order_id),
                    "tid": str(surveyor_team_id) if surveyor_team_id else None,
                    "narrative": narrative,
                    "format": format_type,
                    "gbom": json.dumps(general_bom),
                },
            )

        # 2. Hapus points lama jika ada dan buat ulang
        await self.execute(
            "DELETE FROM work_order_survey_points WHERE work_order_id = CAST(:wo_id AS uuid)",
            {"wo_id": str(work_order_id)},
        )

        for pt in points:
            await self.execute(
                """
                INSERT INTO work_order_survey_points (
                    work_order_id, survey_id, point_name, location_detail,
                    site_lat, site_lng, recommended_work_type_id,
                    recommended_bom, remarks, photos_json, status
                ) VALUES (
                    CAST(:wo_id AS uuid), CAST(:sid AS uuid), :pname, :loc,
                    :lat, :lng, CAST(:wt_id AS uuid),
                    CAST(:rbom AS jsonb), :remarks, CAST(:photos AS jsonb), 'TODO'
                )
                """,
                {
                    "wo_id": str(work_order_id),
                    "sid": str(survey_id),
                    "pname": pt.get("point_name"),
                    "loc": pt.get("location_detail"),
                    "lat": pt.get("site_lat"),
                    "lng": pt.get("site_lng"),
                    "wt_id": str(pt.get("recommended_work_type_id")),
                    "rbom": json.dumps(pt.get("recommended_bom") or []),
                    "remarks": pt.get("remarks"),
                    "photos": json.dumps(pt.get("photos") or []),
                },
            )

        # 3. Update client_work_orders status
        await self.execute(
            """
            UPDATE client_work_orders
            SET status = 'SURVEY_SUBMITTED',
                survey_submitted_at = NOW(),
                update_at = NOW()
            WHERE work_order_id = CAST(:wo_id AS uuid)
            """,
            {"wo_id": str(work_order_id)},
        )

    async def list_survey_points(self, work_order_id: UUID | str) -> Sequence[Any]:
        sql = """
            SELECT
                p.point_id,
                p.work_order_id,
                p.survey_id,
                p.point_name,
                p.location_detail,
                p.site_lat,
                p.site_lng,
                p.recommended_work_type_id,
                wt.name AS recommended_work_type_name,
                p.recommended_bom,
                p.remarks,
                p.photos_json AS photos,
                p.status
            FROM work_order_survey_points p
            LEFT JOIN work_type wt ON wt.work_type_id = p.recommended_work_type_id
            WHERE p.work_order_id = CAST(:wo_id AS uuid) AND p.delete_at IS NULL
            ORDER BY p.create_at ASC
        """
        return await self.fetchall(sql, {"wo_id": str(work_order_id)})

    async def list_items(self, work_order_id: UUID | str) -> Sequence[Any]:
        sql = """
            SELECT
                i.item_id,
                i.work_order_id,
                i.survey_point_id,
                i.work_type_id,
                wt.name AS work_type_name,
                i.title,
                i.location_detail,
                i.target_qty,
                i.completed_qty,
                i.photo_slots_snapshot,
                i.status,
                i.create_at AS created_at
            FROM work_order_items i
            JOIN work_type wt ON wt.work_type_id = i.work_type_id
            WHERE i.work_order_id = CAST(:wo_id AS uuid) AND i.delete_at IS NULL
            ORDER BY i.create_at ASC
        """
        return await self.fetchall(sql, {"wo_id": str(work_order_id)})

    async def list_bom(self, work_order_id: UUID | str) -> Sequence[Any]:
        sql = """
            SELECT
                b.bom_id,
                b.work_order_id,
                b.work_order_item_id,
                b.item_name,
                b.unit,
                b.estimated_qty,
                b.actual_qty
            FROM work_order_bom b
            WHERE b.work_order_id = CAST(:wo_id AS uuid) AND b.delete_at IS NULL
            ORDER BY b.create_at ASC
        """
        return await self.fetchall(sql, {"wo_id": str(work_order_id)})

    async def get_survey(self, work_order_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT survey_id, work_order_id, surveyor_team_id, survey_date,
                   narrative, general_bom, format, status, submitted_at, approved_at
            FROM work_order_surveys
            WHERE work_order_id = CAST(:wo_id AS uuid) AND delete_at IS NULL
            """,
            {"wo_id": str(work_order_id)},
        )

    async def apply_survey_to_items(self, work_order_id: UUID | str, approved_by_user_id: UUID | str) -> None:
        """
        Fitur Inti: PM menyetujui survei.
        1. Ambil survey points.
        2. Salin tiap point menjadi work_order_items dengan photo_slots_snapshot dari work_type.
        3. Salin recommended_bom tiap point menjadi work_order_bom yang terhubung ke item_id.
        4. Salin general_bom menjadi work_order_bom (work_order_item_id = NULL).
        5. Update status client_work_orders ke READY_TO_EXECUTE.
        """
        points = await self.fetchall(
            """
            SELECT point_id, point_name, location_detail, recommended_work_type_id, recommended_bom
            FROM work_order_survey_points
            WHERE work_order_id = CAST(:wo_id AS uuid) AND delete_at IS NULL
            """,
            {"wo_id": str(work_order_id)},
        )

        for pt in points:
            # Ambil template foto dari work_type
            wt_row = await self.fetchone(
                """
                SELECT photo_requirements,
                       COALESCE((SELECT jsonb_agg(jsonb_build_object(
                                     'id', p.image_requirement_id,
                                     'label', p.name,
                                     'hint', p.description,
                                     'required', p.is_mandatory)
                                 ORDER BY p.sort_order)
                                 FROM image_requirement p
                                 WHERE p.work_type_id = wt.work_type_id AND p.delete_at IS NULL
                                ), '[]'::jsonb) AS legacy_photos
                FROM work_type wt
                WHERE wt.work_type_id = CAST(:wt_id AS uuid)
                """,
                {"wt_id": str(pt.recommended_work_type_id)},
            )
            photo_slots = []
            if wt_row:
                if wt_row.photo_requirements and len(wt_row.photo_requirements) > 0:
                    photo_slots = wt_row.photo_requirements
                elif wt_row.legacy_photos and len(wt_row.legacy_photos) > 0:
                    photo_slots = wt_row.legacy_photos

            item_id = await self.scalar(
                """
                INSERT INTO work_order_items (
                    work_order_id, survey_point_id, work_type_id, title,
                    location_detail, target_qty, completed_qty,
                    photo_slots_snapshot, status
                ) VALUES (
                    CAST(:wo_id AS uuid), CAST(:pt_id AS uuid),
                    CAST(:wt_id AS uuid), :title, :loc,
                    1.0, 0.0, CAST(:slots AS jsonb), 'PENDING'
                ) RETURNING item_id
                """,
                {
                    "wo_id": str(work_order_id),
                    "pt_id": str(pt.point_id),
                    "wt_id": str(pt.recommended_work_type_id),
                    "title": pt.point_name,
                    "loc": pt.location_detail,
                    "slots": json.dumps(photo_slots),
                },
            )

            # Insert BOM item
            bom_list = pt.recommended_bom or []
            for b in bom_list:
                item_name = b.get("item_name") or b.get("material_name") or "Material"
                unit = b.get("unit") or "pcs"
                qty = b.get("estimated_qty") or b.get("qty") or 1.0
                await self.execute(
                    """
                    INSERT INTO work_order_bom (
                        work_order_id, work_order_item_id, item_name, unit, estimated_qty, actual_qty
                    ) VALUES (
                        CAST(:wo_id AS uuid), CAST(:item_id AS uuid), :name, :unit, :qty, 0.0
                    )
                    """,
                    {
                        "wo_id": str(work_order_id),
                        "item_id": str(item_id),
                        "name": str(item_name),
                        "unit": str(unit),
                        "qty": Decimal(str(qty)),
                    },
                )

        # General BOM dari survei
        survey = await self.get_survey(work_order_id)
        if survey and survey.general_bom:
            for gb in survey.general_bom:
                item_name = gb.get("item_name") or gb.get("material_name") or "General Material"
                unit = gb.get("unit") or "pcs"
                qty = gb.get("estimated_qty") or gb.get("qty") or 1.0
                await self.execute(
                    """
                    INSERT INTO work_order_bom (
                        work_order_id, work_order_item_id, item_name, unit, estimated_qty, actual_qty
                    ) VALUES (
                        CAST(:wo_id AS uuid), NULL, :name, :unit, :qty, 0.0
                    )
                    """,
                    {
                        "wo_id": str(work_order_id),
                        "name": str(item_name),
                        "unit": str(unit),
                        "qty": Decimal(str(qty)),
                    },
                )

        # Update status work order & survey
        await self.execute(
            """
            UPDATE work_order_surveys
            SET status = 'APPROVED',
                approved_at = NOW(),
                approved_by = CAST(:uid AS uuid),
                update_at = NOW()
            WHERE work_order_id = CAST(:wo_id AS uuid)
            """,
            {"wo_id": str(work_order_id), "uid": str(approved_by_user_id)},
        )

        await self.execute(
            """
            UPDATE client_work_orders
            SET status = 'READY_TO_EXECUTE',
                survey_approved_at = NOW(),
                survey_approved_by = CAST(:uid AS uuid),
                update_at = NOW()
            WHERE work_order_id = CAST(:wo_id AS uuid)
            """,
            {"wo_id": str(work_order_id), "uid": str(approved_by_user_id)},
        )

    async def update_item_progress(
        self,
        item_id: UUID | str,
        completed_qty: Decimal,
        status: str,
        photo_slots_snapshot: list[dict[str, Any]] | None = None,
    ) -> None:
        params: dict[str, Any] = {
            "item_id": str(item_id),
            "completed_qty": completed_qty,
            "status": status,
        }
        sql = """
            UPDATE work_order_items
            SET completed_qty = :completed_qty,
                status = :status,
                update_at = NOW()
        """
        if photo_slots_snapshot is not None:
            sql += ", photo_slots_snapshot = CAST(:slots AS jsonb)"
            params["slots"] = json.dumps(photo_slots_snapshot)

        sql += " WHERE item_id = CAST(:item_id AS uuid)"
        await self.execute(sql, params)

    async def update_bom_actual(self, bom_id: UUID | str, actual_qty: Decimal) -> None:
        await self.execute(
            """
            UPDATE work_order_bom
            SET actual_qty = :actual_qty,
                update_at = NOW()
            WHERE bom_id = CAST(:bom_id AS uuid)
            """,
            {"bom_id": str(bom_id), "actual_qty": actual_qty},
        )

    async def sign_bast(
        self,
        work_order_id: UUID | str,
        signer_name: str,
        signature_file_id: UUID | str | None,
        verify_hash: str,
    ) -> None:
        await self.execute(
            """
            UPDATE client_work_orders
            SET status = 'BAST_SIGNED',
                bast_signed_at = NOW(),
                bast_signer_name = :sname,
                bast_signature_file_id = CAST(:fid AS uuid),
                verify_hash = :vhash,
                update_at = NOW()
            WHERE work_order_id = CAST(:wo_id AS uuid)
            """,
            {
                "wo_id": str(work_order_id),
                "sname": signer_name,
                "fid": str(signature_file_id) if signature_file_id else None,
                "vhash": verify_hash,
            },
        )

    async def insert_signature_file(
        self,
        *,
        file_id: str,
        org_id: UUID | str,
        storage_key: str,
        file_name: str,
        mime_type: str,
        byte_size: int,
        sha256: bytes,
        user_id: UUID | str,
    ) -> str:
        row = await self.fetchone(
            """
            INSERT INTO file_object (
                id, office_id, storage_key, file_name, mime_type, byte_size, sha256, uploaded_by
            )
            VALUES (
                CAST(:fid AS uuid), CAST(:org AS uuid), :storage_key,
                :file_name, :mime_type, :byte_size, :sha256, CAST(:uid AS uuid)
            )
            ON CONFLICT (office_id, sha256) DO UPDATE
            SET file_name = EXCLUDED.file_name
            RETURNING CAST(id AS text) AS id
            """,
            {
                "fid": file_id,
                "org": str(org_id),
                "storage_key": storage_key,
                "file_name": file_name,
                "mime_type": mime_type,
                "byte_size": byte_size,
                "sha256": sha256,
                "uid": str(user_id),
            },
        )
        return str(row.id) if row else file_id

