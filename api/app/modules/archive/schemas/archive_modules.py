"""Konfigurasi tetap modul Arsip (nama tabel/kolom bukan input pengguna)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchiveModule:
    key: str
    label: str
    table: str
    pk: str
    name_col: str
    code_col: str | None
    permission: str
    office_col: str | None = None
    # Ekspresi (`{r}` = alias tabel) yang masing-masing harus unik di antara item aktif.
    unique_exprs: tuple[str, ...] = ()
    # (kolom rujukan, tabel induk, pk induk, nama induk): induk harus aktif agar item boleh dipulihkan.
    parents: tuple[tuple[str, str, str, str], ...] = ()
    conflict_message: str = "Sudah ada data aktif dengan nama atau kode yang sama. Ubah dulu data aktifnya."


ARCHIVE_MODULES: dict[str, ArchiveModule] = {m.key: m for m in (
    ArchiveModule("tools", "Peralatan", "tool", "tool_id", "name", "tool_code", "manage:assets", "office_id",
                  ("{r}.tool_code",), (("division_id", "division", "division_id", "divisi"),),
                  "Kode peralatan ini sudah dipakai peralatan aktif. Ubah kode peralatan aktif itu dulu."),
    ArchiveModule("vehicles", "Kendaraan", "vehicle", "vehicle_id", "name", "number_plate", "manage:assets",
                  "office_id", ("{r}.number_plate",), (("division_id", "division", "division_id", "divisi"),),
                  "Plat nomor ini sudah dipakai kendaraan aktif. Ubah data kendaraan aktif itu dulu."),
    ArchiveModule("clients", "Klien", "client", "client_id", "name", "client_code", "create:plan", None,
                  ("lower({r}.client_code)", "lower(trim({r}.name))"), (),
                  "Klien dengan kode atau nama yang sama sudah ada. Pakai klien yang sudah ada."),
    ArchiveModule("divisions", "Divisi", "division", "division_id", "name", None, "manage:divisions", None, (),
                  (("om_id", "employee", "employee_id", "Operational Manager"),
                   ("pm_id", "employee", "employee_id", "Project Manager"))),
    ArchiveModule("job-positions", "Jabatan", "job_position", "position_id", "name", "code", "manage:users", None,
                  ("lower({r}.code)",), (("division_id", "division", "division_id", "divisi"),),
                  "Kode jabatan ini sudah dipakai jabatan aktif. Ubah kode jabatan aktif itu dulu."),
    ArchiveModule("mess", "Mess", "company_mess", "mess_id", "mess_name", None, "manage:mess", None),
)}
