"""Tim lapangan uji per divisi (CCTV, ACS, Electrical, Wall Display) + anggotanya.

- Tim CCTV & ACS yang sudah ada mendapat 2 anggota tambahan.
- Tim Electrical (ketua Eko Prasetyo) & Tim Wall Display (ketua Hendra Gunawan) dibuat; peran akun ketua → TEAM_LEADER.
Akun memakai sandi seed yang sudah ada. Aman diulang (idempoten), tidak menghapus apa pun.

    cd api
    .venv/Scripts/python.exe ../scripts/seed_tim_lapangan.py [--uji-kering]
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from sqlalchemy import text  # noqa: E402

from app.database.session import engine  # noqa: E402

# divisi → (nama tim, email ketua, [email anggota])
TEAMS = {
    "Divisi CCTV & Keamanan Elektronik": ("Tim Uji Survei CCTV", "zulkifli@visiontech.id",
                                          ["agengprayoga@visiontech.id", "ahmadfauzi@visiontech.id"]),
    "Divisi Access Control System (ACS)": ("Tim Uji Survei ACS", "yudisetiawan@visiontech.id",
                                           ["bayusaputra@visiontech.id", "muhammadiqbal@visiontech.id"]),
    "Divisi Electrical & Arus Kuat": ("Tim Electrical", "ekoprasetyo@visiontech.id",
                                      ["feriirawan@visiontech.id", "gilangramadhan@visiontech.id"]),
    "Divisi Wall Display & LED Screen": ("Tim Wall Display", "hendragunawan@visiontech.id",
                                         ["putriwulandari@visiontech.id", "rianhidayat@visiontech.id"]),
}

PMS = {
    "Divisi CCTV & Keamanan Elektronik": "budisantoso@visiontech.id",
    "Divisi Access Control System (ACS)": "dedikurniawan@visiontech.id",
    "Divisi Electrical & Arus Kuat": "arifhidayat@visiontech.id",
    "Divisi Wall Display & LED Screen": "fajarnugraha@visiontech.id",
}


async def employee(conn, email: str):
    row = (await conn.execute(text(
        "SELECT e.employee_id, e.office_id FROM users u JOIN employee e USING (employee_id) "
        "WHERE lower(u.email) = lower(:m) AND u.delete_at IS NULL"), {"m": email})).first()
    if row is None:
        raise SystemExit(f"Akun {email} tidak ada.")
    return row


async def main(dry_run: bool) -> None:
    async with engine.connect() as conn:
        tx = await conn.begin()
        for division, (team_name, leader_mail, members) in TEAMS.items():
            div = (await conn.execute(text(
                "SELECT division_id FROM division WHERE name = :n AND delete_at IS NULL"), {"n": division})).scalar()
            if div is None:
                print(f"- lewati {division}: tidak ada")
                continue
            leader = await employee(conn, leader_mail)
            await conn.execute(text(
                "UPDATE users SET system_role = 'TEAM_LEADER', update_at = now() WHERE employee_id = :e "
                "AND system_role = 'EMPLOYEE'"), {"e": leader.employee_id})
            team = (await conn.execute(text(
                "SELECT team_id FROM team WHERE name = :n AND division_id = :d AND delete_at IS NULL"),
                {"n": team_name, "d": div})).scalar()
            if team is None:
                team = (await conn.execute(text(
                    "INSERT INTO team (office_id, division_id, leader_employee_id, name, status) "
                    "VALUES (:o, :d, :l, :n, TRUE) RETURNING team_id"),
                    {"o": leader.office_id, "d": div, "l": leader.employee_id, "n": team_name})).scalar()
                print(f"+ {team_name}")
            for mail in [leader_mail, *members]:
                emp = await employee(conn, mail)
                exists = (await conn.execute(text(
                    "SELECT 1 FROM member WHERE team_id = :t AND employee_id = :e AND delete_at IS NULL"),
                    {"t": team, "e": emp.employee_id})).first()
                if not exists:
                    await conn.execute(text(
                        "INSERT INTO member (team_id, employee_id, is_active) VALUES (:t, :e, TRUE)"),
                        {"t": team, "e": emp.employee_id})
                    print(f"  + anggota {mail}")
        # PM per divisi (tiap PM hanya melihat jadwal divisinya) + divisi karyawan = divisi timnya.
        for division, pm_mail in PMS.items():
            div = (await conn.execute(text(
                "SELECT division_id FROM division WHERE name = :n AND delete_at IS NULL"), {"n": division})).scalar()
            if div is None:
                continue
            pm = await employee(conn, pm_mail)
            await conn.execute(text("UPDATE division SET pm_id = :p, update_at = now() WHERE division_id = :d"),
                               {"p": pm.employee_id, "d": div})
            await conn.execute(text(
                "UPDATE users SET system_role = 'PROJECT_MANAGER', update_at = now() WHERE employee_id = :e"),
                {"e": pm.employee_id})
            _, leader_mail, members = TEAMS[division]
            for mail in [pm_mail, leader_mail, *members]:
                emp = await employee(conn, mail)
                await conn.execute(text("UPDATE employee SET division_id = :d WHERE employee_id = :e"),
                                   {"d": div, "e": emp.employee_id})
            print(f"= PM {division}: {pm_mail}")
            # Pekerjaan klien divisi ini dikelola PM divisinya (data uji lama dibuat atas nama satu PM).
            await conn.execute(text(
                "UPDATE work_completion SET pm_id = :p, update_at = now() WHERE division_id = :d "
                "AND delete_at IS NULL AND pm_id IS DISTINCT FROM :p"), {"p": pm.employee_id, "d": div})
        # Nomor HP uji (0812-0000-xxxx) untuk PM, ketua, dan anggota yang belum punya — kontak telepon/WhatsApp.
        mails = list(PMS.values()) + [m for _, lead, mem in TEAMS.values() for m in [lead, *mem]]
        for n, mail in enumerate(mails, start=1):
            emp = await employee(conn, mail)
            await conn.execute(text(
                "UPDATE employee SET phone_number = :p WHERE employee_id = :e AND phone_number IS NULL"),
                {"p": f"0812-0000-{n:04d}", "e": emp.employee_id})
        if dry_run:
            await tx.rollback()
            print("uji kering: dibatalkan")
        else:
            await tx.commit()
            print("selesai")


if __name__ == "__main__":
    asyncio.run(main("--uji-kering" in sys.argv))
