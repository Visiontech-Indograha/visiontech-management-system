"""
app/modules/employees/repositories/employee_repository.py
Karyawan V2. Relasi: employee N─1 office, N─1 division (opsional), N─1 job_position (opsional), 1─N address,
1─1 users. Foto = file_object.storage_key di `photo_path` (dikembalikan sebagai id file_object).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.hard_delete import purge_row
from app.core.repository import BaseRepository, escape_like
from app.shared.access.scope_rules import employee_sensitive_sql, employee_visible_sql

# Cakupan default = tanpa pembatasan (pemanggil internal). Pengguna biasa memakai `employee_params(user)`.
UNSCOPED: dict[str, Any] = {"dir_all": True, "sens_all": True, "sens_offices": [], "viewer_emp": None, "pm": False}

_SELECT = f"""
    SELECT e.employee_id, e.employee_no, e.full_name, e.office_id, o.name AS office_name,
           e.division_id, d.name AS division_name, e.position_id, jp.code AS position_code, jp.name AS position_name,
           (e.join_date AT TIME ZONE 'Asia/Jakarta')::date AS join_date,
           (e.pkwt_end_date AT TIME ZONE 'Asia/Jakarta')::date AS pkwt_end_date, e.phone_number,
           (SELECT f.id FROM file_object f WHERE f.storage_key = e.photo_path LIMIT 1) AS photo_file_id,
           (e.face_embedding IS NOT NULL) AS face_enrolled, e.offboarding_status::text AS offboarding_status,
           (e.delete_at IS NOT NULL) AS archived,
           u.user_id, u.email, u.system_role::text AS system_role, u.is_active AS account_active,
           (SELECT a.city FROM address a WHERE a.employee_id = e.employee_id AND a.delete_at IS NULL
            ORDER BY a.create_at LIMIT 1) AS city,
           e.create_at, e.update_at,
           {employee_sensitive_sql("e.employee_id")} AS sensitive_ok
    FROM employee e
    JOIN office o ON o.office_id = e.office_id
    LEFT JOIN division d ON d.division_id = e.division_id
    LEFT JOIN job_position jp ON jp.position_id = e.position_id
    LEFT JOIN users u ON u.employee_id = e.employee_id AND u.delete_at IS NULL
"""
_FILTER = """
    WHERE (CASE WHEN CAST(:status AS varchar) = 'archived' THEN e.delete_at IS NOT NULL ELSE e.delete_at IS NULL END)
      AND (CAST(:status AS varchar) IS NULL OR CAST(:status AS varchar) IN ('all', 'archived')
           OR e.offboarding_status::text = CAST(:status AS varchar))
      AND (CAST(:div AS uuid) IS NULL OR e.division_id = CAST(:div AS uuid))
      AND (CAST(:office AS uuid) IS NULL OR e.office_id = CAST(:office AS uuid))
      AND (CAST(:pos AS uuid) IS NULL OR e.position_id = CAST(:pos AS uuid))
      AND (CAST(:q AS varchar) IS NULL OR e.full_name ILIKE '%' || CAST(:q AS varchar) || '%'
           OR e.employee_no ILIKE '%' || CAST(:q AS varchar) || '%' OR u.email ILIKE '%' || CAST(:q AS varchar) || '%')
      AND (CAST(:dir_all AS boolean) OR """ + employee_visible_sql("e.employee_id") + """)
"""
_UUIDS = ("office_id", "division_id", "position_id")


class EmployeeRepository(BaseRepository):
    """Query karyawan V2."""

    async def employee_of_user(self, user_id: UUID | str) -> UUID | None:
        emp: UUID | None = await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": str(user_id)},
        )
        return emp

    async def lock(self, employee_id: UUID | str, org_id: UUID | str | None = None) -> Any:
        """Baris karyawan untuk transaksi (dipakai juga modul accounts)."""
        return await self.fetchone(
            """
            SELECT employee_id AS id, delete_at IS NOT NULL AS deleted,
                   (offboarding_status <> 'offboarded') AS is_active, offboarding_status::text AS offboarding_status
            FROM employee WHERE employee_id = CAST(:id AS uuid) FOR UPDATE
            """,
            {"id": str(employee_id)},
        )

    def _params(self, *, status: str | None, division_id: UUID | None, office_id: UUID | None,
                position_id: UUID | None, q: str | None, scope: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"status": status, "div": str(division_id) if division_id else None,
                "office": str(office_id) if office_id else None, "pos": str(position_id) if position_id else None,
                "q": escape_like(q), **(scope or UNSCOPED)}

    async def count(self, scope: dict[str, Any] | None = None, **filters: Any) -> int:
        n = await self.scalar(
            "SELECT COUNT(*) FROM employee e LEFT JOIN users u ON u.employee_id = e.employee_id "
            "AND u.delete_at IS NULL" + _FILTER, self._params(scope=scope, **filters))
        return int(n or 0)

    async def page(self, limit: int, offset: int, scope: dict[str, Any] | None = None, **filters: Any) -> list[Any]:
        return list(await self.fetchall(
            _SELECT + _FILTER + " ORDER BY e.full_name LIMIT :limit OFFSET :offset",
            {**self._params(scope=scope, **filters), "limit": limit, "offset": offset},
        ))

    async def get(self, employee_id: UUID | str, scope: dict[str, Any] | None = None) -> Any:
        """Karyawan satu baris; di luar cakupan `scope` → None (pemanggil mengubahnya menjadi 404)."""
        return await self.fetchone(
            _SELECT + " WHERE e.employee_id = CAST(:id AS uuid) AND (CAST(:dir_all AS boolean) OR "
            + employee_visible_sql("e.employee_id") + ")",
            {"id": str(employee_id), **(scope or UNSCOPED)},
        )

    async def addresses(self, employee_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            "SELECT address_id, address_line, city, postal_code FROM address "
            "WHERE employee_id = CAST(:id AS uuid) AND delete_at IS NULL ORDER BY create_at",
            {"id": str(employee_id)},
        ))

    # ── Validasi referensi ────────────────────────────────────────────────────
    async def recent_employee_nos(self, limit: int = 300) -> list[str]:
        """Nomor karyawan terbaru (termasuk yang diarsipkan, agar nomor tidak dipakai ulang)."""
        rows = await self.fetchall(
            "SELECT employee_no FROM employee ORDER BY create_at DESC LIMIT :n", {"n": limit}
        )
        return [str(r.employee_no) for r in rows]

    async def employee_no_taken(self, employee_no: str, exclude: UUID | None = None) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM employee WHERE employee_no = :no AND delete_at IS NULL "
            "AND (CAST(:ex AS uuid) IS NULL OR employee_id <> CAST(:ex AS uuid)))",
            {"no": employee_no, "ex": str(exclude) if exclude else None},
        ))

    async def refs(self, office_id: UUID | None, division_id: UUID | None, position_id: UUID | None) -> Any:
        """Kantor ada? divisi aktif? jabatan aktif & divisinya (NULL = lintas divisi)?"""
        return await self.fetchone(
            """
            SELECT (CAST(:office AS uuid) IS NULL OR EXISTS (SELECT 1 FROM office
                    WHERE office_id = CAST(:office AS uuid)
                    AND delete_at IS NULL)) AS office_ok,
                   (CAST(:div AS uuid) IS NULL OR EXISTS (SELECT 1 FROM division WHERE division_id = CAST(:div AS uuid)
                    AND delete_at IS NULL AND status)) AS division_ok,
                   (CAST(:pos AS uuid) IS NULL OR EXISTS (SELECT 1 FROM job_position
                    WHERE position_id = CAST(:pos AS uuid) AND delete_at IS NULL AND status)) AS position_ok,
                   (SELECT division_id FROM job_position WHERE position_id = CAST(:pos AS uuid)) AS position_division
            """,
            {"office": str(office_id) if office_id else None, "div": str(division_id) if division_id else None,
             "pos": str(position_id) if position_id else None},
        )

    async def image_key(self, file_id: UUID) -> str | None:
        key: str | None = await self.scalar(
            "SELECT storage_key FROM file_object WHERE id = CAST(:id AS uuid) AND mime_type LIKE 'image/%'",
            {"id": str(file_id)},
        )
        return key

    async def uploaded_image_key(self, file_id: UUID, user_id: UUID | str) -> str | None:
        """
        storage_key gambar yang boleh dijadikan foto sendiri: unggahan pengguna ini, atau gambar yang sudah menjadi foto
        profil karyawan lain. Unggahan dideduplikasi per kantor (SHA-256): gambar yang sama persis dari akun kedua
        mengembalikan baris milik pengunggah pertama, dan foto profil memang sudah terlihat oleh pemegang `view:users`,
        jadi memakainya tidak membuka akses baru. Berkas selfie/dokumen orang lain tetap tidak bisa dipakai.
        """
        key: str | None = await self.scalar(
            """
            SELECT f.storage_key FROM file_object f
            WHERE f.id = CAST(:id AS uuid) AND f.mime_type LIKE 'image/%'
              AND (f.uploaded_by = CAST(:uid AS uuid)
                   OR EXISTS (SELECT 1 FROM employee e
                              WHERE e.profile_photo_path = f.storage_key OR e.photo_path = f.storage_key))
            """,
            {"id": str(file_id), "uid": str(user_id)},
        )
        return key

    async def profile_photo_file_id(self, employee_id: UUID) -> UUID | None:
        photo_id: UUID | None = await self.scalar(
            "SELECT f.id FROM file_object f JOIN employee e ON e.profile_photo_path = f.storage_key "
            "WHERE e.employee_id = CAST(:id AS uuid)",
            {"id": str(employee_id)},
        )
        return photo_id

    # ── Tulis ─────────────────────────────────────────────────────────────────
    async def insert(self, data: dict[str, Any]) -> UUID:
        new_id: UUID = await self.scalar(
            """
            INSERT INTO employee (office_id, division_id, position_id, full_name, employee_no, join_date,
                                  pkwt_end_date, phone_number, photo_path, profile_photo_path)
            VALUES (CAST(:office_id AS uuid), CAST(:division_id AS uuid), CAST(:position_id AS uuid), :full_name,
                    :employee_no, (CAST(:join_date AS date)::timestamp AT TIME ZONE 'Asia/Jakarta'),
                    (CAST(:pkwt_end_date AS date)::timestamp AT TIME ZONE 'Asia/Jakarta'),
                    :phone_number, :photo_path, :photo_path)
            RETURNING employee_id
            """,
            {**data, **{k: str(data[k]) if data.get(k) else None for k in _UUIDS}},
        )
        return new_id

    async def update(self, employee_id: UUID, fields: dict[str, Any]) -> None:
        if not fields:
            return
        casts = dict.fromkeys(_UUIDS, "uuid")
        # Tanggal kerja = tengah malam WIB (kolom timestamptz) — tidak bergeser sehari di sesi berzona UTC.
        dates = {"join_date", "pkwt_end_date"}
        sets = []
        for k in fields:
            col = k
            if k in dates:
                sets.append(f"{col} = (CAST(:{k} AS date)::timestamp AT TIME ZONE 'Asia/Jakarta')")
            else:
                sets.append(f"{col} = CAST(:{k} AS {casts[k]})" if k in casts else f"{col} = :{k}")
            if k == "photo_path":
                sets.append("profile_photo_path = :photo_path")
        await self.execute(
            f"UPDATE employee SET {', '.join(sets)}, update_at = now() WHERE employee_id = CAST(:id AS uuid)",
            {**{k: (str(v) if k in _UUIDS and v else v) for k, v in fields.items()}, "id": str(employee_id)},
        )

    async def add_address(self, employee_id: UUID | str, data: dict[str, Any]) -> Any:
        return await self.fetchone(
            "INSERT INTO address (employee_id, address_line, city, postal_code) "
            "VALUES (CAST(:emp AS uuid), :address_line, :city, :postal_code) "
            "RETURNING address_id, address_line, city, postal_code",
            {**data, "emp": str(employee_id)},
        )

    async def update_address(self, employee_id: UUID, address_id: UUID, data: dict[str, Any]) -> Any:
        return await self.fetchone(
            "UPDATE address SET address_line = :address_line, city = :city, postal_code = :postal_code, "
            "update_at = now() WHERE address_id = CAST(:id AS uuid) AND employee_id = CAST(:emp AS uuid) "
            "AND delete_at IS NULL RETURNING address_id, address_line, city, postal_code",
            {**data, "id": str(address_id), "emp": str(employee_id)},
        )

    async def delete_address(self, employee_id: UUID, address_id: UUID) -> bool:
        done = await self.scalar(
            "UPDATE address SET delete_at = now(), update_at = now() WHERE address_id = CAST(:id AS uuid) "
            "AND employee_id = CAST(:emp AS uuid) AND delete_at IS NULL RETURNING address_id",
            {"id": str(address_id), "emp": str(employee_id)},
        )
        return done is not None

    async def archive(self, employee_id: UUID) -> None:
        """Arsip (soft delete) karyawan yang sudah offboarded; akun ikut diarsipkan."""
        params = {"id": str(employee_id)}
        await self.execute("UPDATE employee SET delete_at = now(), update_at = now() "
                           "WHERE employee_id = CAST(:id AS uuid)", params)
        await self.execute("UPDATE users SET is_active = FALSE, delete_at = now(), update_at = now() "
                           "WHERE employee_id = CAST(:id AS uuid)", params)

    async def photo_keys(self, employee_id: UUID) -> list[str]:
        """Kunci berkas MinIO milik karyawan (foto), untuk dibersihkan setelah hapus permanen."""
        row = await self.fetchone("SELECT photo_path, profile_photo_path FROM employee "
                                  "WHERE employee_id = CAST(:id AS uuid)", {"id": str(employee_id)})
        return [k for k in (row or ()) if k]

    async def clear_face_embedding(self, employee_id: UUID) -> None:
        """Kosongkan data biometrik (embedding wajah) sebelum baris dihapus."""
        await self.execute("UPDATE employee SET face_embedding = NULL WHERE employee_id = CAST(:id AS uuid)",
                           {"id": str(employee_id)})

    async def hard_delete(self, employee_id: UUID) -> None:
        """Hapus permanen: akun login (beserta sesinya) dulu, lalu karyawan beserta semua rujukannya."""
        for (uid,) in (await self.fetchall("SELECT user_id FROM users WHERE employee_id = CAST(:id AS uuid)",
                                           {"id": str(employee_id)})):
            await purge_row(self.db, "users", "user_id", uid)
        await purge_row(self.db, "employee", "employee_id", employee_id)

    async def separated_at(self, employee_id: UUID) -> Any:
        """Waktu karyawan keluar (selesai offboarding); None bila belum/tidak tercatat."""
        row = await self.fetchone("SELECT separated_at FROM employee WHERE employee_id = CAST(:id AS uuid)",
                                  {"id": str(employee_id)})
        return row[0] if row else None

    async def restore(self, employee_id: UUID) -> None:
        """Batal arsip: data kembali terlihat, status tetap offboarded (akses baru lewat HR)."""
        params = {"id": str(employee_id)}
        await self.execute("UPDATE employee SET delete_at = NULL, update_at = now() "
                           "WHERE employee_id = CAST(:id AS uuid)", params)
        await self.execute("UPDATE users SET delete_at = NULL, update_at = now() "
                           "WHERE employee_id = CAST(:id AS uuid)", params)


CRUDEmployee = EmployeeRepository
