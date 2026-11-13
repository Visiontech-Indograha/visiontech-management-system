"""
api/app/modules/hse/repositories/hse_campaign_repository.py

Repositori akses basis data untuk kampanye K3 dan pelacakan audit pembaca.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.hse.schemas.hse_schema import HseAcknowledgeCreate, HseCampaignCreate, HseCampaignUpdate


class HseCampaignRepository(BaseRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def create(self, data: HseCampaignCreate, created_by_id: UUID) -> dict[str, Any]:
        query = """
            INSERT INTO hse_campaigns (
                title, summary, content_html, media_path, media_paths, media_captions, target_audience,
                target_user_ids, is_mandatory, cooldown_seconds, start_date, end_date,
                is_active, created_by_id
            )
            VALUES (
                :title, :summary, :content_html, :media_path, CAST(:media_paths AS jsonb),
                CAST(:media_captions AS jsonb), :target_audience,
                CAST(:target_user_ids AS jsonb), :is_mandatory, :cooldown_seconds, :start_date, :end_date,
                :is_active, :created_by_id
            )
            RETURNING
                campaign_id, title, summary, content_html, media_path, media_paths, media_captions, target_audience,
                target_user_ids, is_mandatory, cooldown_seconds, start_date, end_date,
                is_active, created_by_id, create_at, update_at;
        """
        params = {
            "title": data.title,
            "summary": data.summary,
            "content_html": data.content_html,
            "media_path": data.media_path,
            "media_paths": json.dumps([str(u) for u in data.media_paths]),
            "media_captions": json.dumps(list(data.media_captions)),
            "target_audience": data.target_audience,
            "target_user_ids": json.dumps([str(u) for u in data.target_user_ids]) if data.target_user_ids else None,
            "is_mandatory": data.is_mandatory,
            "cooldown_seconds": data.cooldown_seconds,
            "start_date": data.start_date,
            "end_date": data.end_date,
            "is_active": data.is_active,
            "created_by_id": created_by_id,
        }
        row = await self.fetchone(query, params)
        return dict(row._mapping) if row else {}

    async def get_by_id(self, campaign_id: UUID) -> dict[str, Any] | None:
        query = """
            SELECT
                c.campaign_id, c.title, c.summary, c.content_html, c.media_path, c.media_paths, c.media_captions,
                c.target_audience,
                c.target_user_ids, c.is_mandatory, c.cooldown_seconds, c.start_date, c.end_date,
                c.is_active, c.created_by_id, c.create_at, c.update_at,
                COALESCE(e.full_name, u.email) AS creator_name,
                COUNT(a.acknowledgment_id) AS total_readers
            FROM hse_campaigns c
            LEFT JOIN users u ON u.user_id = c.created_by_id
            LEFT JOIN employee e ON e.employee_id = u.employee_id
            LEFT JOIN hse_campaign_acknowledgments a ON a.campaign_id = c.campaign_id
            WHERE c.campaign_id = :campaign_id AND c.delete_at IS NULL
            GROUP BY c.campaign_id, e.full_name, u.email;
        """
        row = await self.fetchone(query, {"campaign_id": campaign_id})
        return dict(row._mapping) if row else None

    async def list_campaigns(
        self,
        limit: int = 50,
        offset: int = 0,
        is_active: bool | None = None,
        target_audience: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        conditions = ["c.delete_at IS NULL"]
        params: dict[str, Any] = {"limit": limit + offset}

        if is_active is not None:
            conditions.append("c.is_active = :is_active")
            params["is_active"] = is_active

        if target_audience:
            conditions.append("c.target_audience = :target_audience")
            params["target_audience"] = target_audience

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT
                c.campaign_id, c.title, c.summary, c.content_html, c.media_path, c.media_paths, c.media_captions,
                c.target_audience,
                c.target_user_ids, c.is_mandatory, c.cooldown_seconds, c.start_date, c.end_date,
                c.is_active, c.created_by_id, c.create_at, c.update_at,
                COALESCE(e.full_name, u.email) AS creator_name,
                COUNT(a.acknowledgment_id) AS total_readers
            FROM hse_campaigns c
            LEFT JOIN users u ON u.user_id = c.created_by_id
            LEFT JOIN employee e ON e.employee_id = u.employee_id
            LEFT JOIN hse_campaign_acknowledgments a ON a.campaign_id = c.campaign_id
            WHERE {where_clause}
            GROUP BY c.campaign_id, e.full_name, u.email
            ORDER BY c.create_at DESC
            LIMIT :limit;
        """
        rows = await self.fetchall(query, params)
        return [dict(r._mapping) for r in rows][offset:]

    async def update(self, campaign_id: UUID, data: HseCampaignUpdate) -> dict[str, Any] | None:
        fields: list[str] = []
        params: dict[str, Any] = {"campaign_id": campaign_id}

        if data.title is not None:
            fields.append("title = :title")
            params["title"] = data.title
        if data.summary is not None:
            fields.append("summary = :summary")
            params["summary"] = data.summary
        if data.content_html is not None:
            fields.append("content_html = :content_html")
            params["content_html"] = data.content_html
        if data.media_path is not None:
            fields.append("media_path = :media_path")
            params["media_path"] = data.media_path
        if data.media_paths is not None:
            fields.append("media_paths = CAST(:media_paths AS jsonb)")
            params["media_paths"] = json.dumps([str(u) for u in data.media_paths])
        if data.media_captions is not None:
            fields.append("media_captions = CAST(:media_captions AS jsonb)")
            params["media_captions"] = json.dumps(list(data.media_captions))
        if data.target_audience is not None:
            fields.append("target_audience = :target_audience")
            params["target_audience"] = data.target_audience
        if data.target_user_ids is not None:
            fields.append("target_user_ids = CAST(:target_user_ids AS jsonb)")
            params["target_user_ids"] = json.dumps([str(u) for u in data.target_user_ids])
        if data.is_mandatory is not None:
            fields.append("is_mandatory = :is_mandatory")
            params["is_mandatory"] = data.is_mandatory
        if data.cooldown_seconds is not None:
            fields.append("cooldown_seconds = :cooldown_seconds")
            params["cooldown_seconds"] = data.cooldown_seconds
        if data.start_date is not None:
            fields.append("start_date = :start_date")
            params["start_date"] = data.start_date
        if data.end_date is not None:
            fields.append("end_date = :end_date")
            params["end_date"] = data.end_date
        if data.is_active is not None:
            fields.append("is_active = :is_active")
            params["is_active"] = data.is_active

        if not fields:
            return await self.get_by_id(campaign_id)

        fields.append("update_at = NOW()")
        set_clause = ", ".join(fields)
        query = f"""
            UPDATE hse_campaigns
            SET {set_clause}
            WHERE campaign_id = :campaign_id AND delete_at IS NULL
            RETURNING campaign_id;
        """
        row = await self.fetchone(query, params)
        if not row:
            return None
        return await self.get_by_id(campaign_id)

    async def delete(self, campaign_id: UUID) -> bool:
        query = """
            UPDATE hse_campaigns
            SET delete_at = NOW(), is_active = FALSE
            WHERE campaign_id = :campaign_id AND delete_at IS NULL
            RETURNING campaign_id;
        """
        row = await self.fetchone(query, {"campaign_id": campaign_id})
        return bool(row)

    async def get_active_popup_for_user(
        self,
        user_id: UUID,
        system_role: str,
        roles: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """
        Mencari kampanye K3 aktif hari ini yang belum dibaca (acknowledged) oleh pengguna.
        Memfilter target_audience:
        - ALL: seluruh pengguna
        - FIELD: TEAM_LEADER, EMPLOYEE
        - OFFICE: SUPER_ADMIN, OPERATIONAL_MANAGER, PROJECT_MANAGER, ADMIN_HR_GA, FINANCE, HSE
        - INDIVIDUAL: jika user_id ada dalam target_user_ids JSONB
        Popup tetap muncul sampai pengguna mengonfirmasi (acknowledgment); memuat ulang tidak menyelesaikannya.
        """
        # `roles` = peran efektif (utama + penugasan aktif, ADR 0002); None = hanya peran utama (perilaku lama).
        # Peran lapangan -> kampanye FIELD, peran kantor -> OFFICE; orang berperan ganda melihat keduanya.
        effective = roles if roles else [system_role]
        field_roles = ("TEAM_LEADER", "EMPLOYEE")
        is_field = any(r in field_roles for r in effective)
        is_office = any(r not in field_roles for r in effective)
        query = """
            SELECT
                c.campaign_id, c.title, c.summary, c.content_html, c.media_path, c.media_paths, c.media_captions,
                c.target_audience, c.is_mandatory, c.cooldown_seconds,
                c.start_date, c.end_date, c.create_at
            FROM hse_campaigns c
            WHERE c.is_active = TRUE
              AND c.delete_at IS NULL
              AND CURRENT_DATE BETWEEN c.start_date AND c.end_date
              AND (
                  c.target_audience = 'ALL'
                  OR (:is_field = TRUE AND c.target_audience = 'FIELD')
                  OR (:is_office = TRUE AND c.target_audience = 'OFFICE')
                  OR (
                      c.target_audience = 'INDIVIDUAL'
                      AND c.target_user_ids IS NOT NULL
                      AND c.target_user_ids ? :user_id_str
                  )
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM hse_campaign_acknowledgments ack
                  WHERE ack.campaign_id = c.campaign_id
                    AND ack.user_id = :user_id
              )
            ORDER BY c.is_mandatory DESC, c.create_at DESC
            LIMIT 1;
        """
        params = {
            "user_id": user_id,
            "user_id_str": str(user_id),
            "is_field": is_field,
            "is_office": is_office,
        }
        row = await self.fetchone(query, params)
        return dict(row._mapping) if row else None

    async def record_acknowledgment(
        self,
        campaign_id: UUID,
        user_id: UUID,
        data: HseAcknowledgeCreate,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        query = """
            INSERT INTO hse_campaign_acknowledgments (
                campaign_id, user_id, platform, device_info,
                ip_address, scroll_completed, read_duration_seconds
            )
            VALUES (
                :campaign_id, :user_id, :platform, :device_info,
                CAST(:ip_address AS inet), :scroll_completed, :read_duration_seconds
            )
            ON CONFLICT (campaign_id, user_id) DO NOTHING
            RETURNING
                acknowledgment_id, campaign_id, user_id, platform,
                device_info, ip_address, scroll_completed,
                read_duration_seconds, acknowledged_at;
        """
        # Sanitasi alamat IP untuk tipe data inet postgres
        sanitized_ip = ip_address if ip_address and ip_address not in ("unknown", "testclient") else None
        params = {
            "campaign_id": campaign_id,
            "user_id": user_id,
            "platform": data.platform,
            "device_info": data.device_info,
            "ip_address": sanitized_ip,
            "scroll_completed": data.scroll_completed,
            "read_duration_seconds": data.read_duration_seconds,
        }
        row = await self.fetchone(query, params)
        if row is None:
            # Sudah pernah dibaca: kembalikan catatan pertama tanpa mencatat pembacaan kedua.
            existing = await self.fetchone(
                """
                SELECT acknowledgment_id, campaign_id, user_id, platform,
                       device_info, ip_address, scroll_completed,
                       read_duration_seconds, acknowledged_at
                FROM hse_campaign_acknowledgments
                WHERE campaign_id = :campaign_id AND user_id = :user_id;
                """,
                {"campaign_id": campaign_id, "user_id": user_id},
            )
            return dict(existing._mapping) if existing else {}
        return dict(row._mapping)

    async def list_readers_by_campaign(
        self, campaign_id: UUID, offices: list[str] | None = None,
    ) -> Sequence[dict[str, Any]]:
        office_filter = "AND e.office_id = ANY(CAST(:offices AS uuid[]))" if offices is not None else ""
        query = f"""
            SELECT
                a.acknowledgment_id, a.campaign_id, a.user_id,
                COALESCE(e.full_name, u.email) AS full_name,
                u.email,
                e.employee_no,
                a.platform,
                a.device_info,
                HOST(a.ip_address) AS ip_address,
                a.scroll_completed,
                a.read_duration_seconds,
                a.acknowledged_at
            FROM hse_campaign_acknowledgments a
            JOIN users u ON u.user_id = a.user_id
            LEFT JOIN employee e ON e.employee_id = u.employee_id
            WHERE a.campaign_id = :campaign_id {office_filter}
            ORDER BY a.acknowledged_at DESC;
        """
        params: dict[str, Any] = {"campaign_id": campaign_id}
        if offices is not None:
            params["offices"] = offices
        rows = await self.fetchall(query, params)
        return [dict(r._mapping) for r in rows]

    async def get_media_files(self, file_ids: list[UUID]) -> dict[str, dict[str, Any]]:
        """Metadata berkas foto yang dirujuk kampanye, dikunci per id (string)."""
        if not file_ids:
            return {}
        query = """
            SELECT CAST(id AS text) AS id, mime_type, byte_size, uploaded_by
            FROM file_object
            WHERE id = ANY(CAST(:file_ids AS uuid[]))
        """
        rows = await self.fetchall(query, {"file_ids": [str(u) for u in file_ids]})
        return {r._mapping["id"]: dict(r._mapping) for r in rows}
