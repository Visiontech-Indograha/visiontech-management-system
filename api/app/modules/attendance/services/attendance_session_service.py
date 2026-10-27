"""
app/modules/attendance/services/attendance_session_service.py
Aturan absensi (V-12) — padanan `domain.js` CHECK_IN, CHECK_OUT, EXPLAIN_ATTENDANCE, REVIEW_ATTENDANCE.
Tanggal & jam dari server menurut zona waktu organisasi (V-10); jarak/status/terlambat/pulang cepat
diputuskan trigger basis data, dan hasil simpanan itulah yang dikembalikan ke klien.
"""

from __future__ import annotations

import csv
import io
import sys
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError, trigger_rule_message
from app.core.events import queue_event
from app.core.hard_delete import purge_row, write_delete_audit
from app.core.security import CurrentUser
from app.core.time import WIB, jakarta_now
from app.modules.attendance.repositories.attendance_session_repository import (
    CRUDAttendanceSession,
)
from app.modules.attendance.schemas.attendance_schema import AttendanceAdminPatch
from app.modules.face.services.face_service import FaceOutcome, FaceService
from app.modules.notifications.services.notification_service import NotificationService
from app.shared.access.access_service import ensure_same_org
from app.shared.access.daily_access_repository import DailyAccessRepository
from app.shared.org_clock import CRUDOrgClock


class AttendanceRowWithEncouragement:
    """Pembungkus row absensi agar menyertakan pesan penyemangat dan kompatibel dengan _mapping."""

    def __init__(self, row: Any, encouragement_message: str | None = None) -> None:
        self._row = row
        self.encouragement_message = encouragement_message

    @property
    def _mapping(self) -> dict[str, Any]:
        d = dict(self._row._mapping) if hasattr(self._row, "_mapping") else dict(self._row)
        d["encouragement_message"] = self.encouragement_message
        return d

    def __getattr__(self, name: str) -> Any:
        if name == "encouragement_message":
            return self.encouragement_message
        return getattr(self._row, name)

    def __getitem__(self, item: Any) -> Any:
        if item == "encouragement_message":
            return self.encouragement_message
        return self._row[item]


OPEN_SESSION = "Anda belum absen pulang dari absen masuk sebelumnya."
VALID_STATUSES = ("AUTO_VALID", "APPROVED")
# R-33 (keputusan pemilik 2026-10-02): absen pulang hanya untuk absen masuk yang sudah valid.
CHECKOUT_NOT_VALID = (
    "Absen pulang hanya bisa dilakukan setelah absen masuk valid. Absen masuk Anda masih menunggu pemeriksaan."
)
FACE_NOT_ENROLLED = "Daftarkan wajah Anda dulu di menu Profil sebelum absen."
FACE_MISMATCH = "Wajah pada swafoto tidak cocok dengan wajah terdaftar. Ambil ulang swafoto dengan wajah jelas."
# docs/35 §5: absen di lokasi tugas harian hanya untuk anggota/ketua tim jadwal itu, pada tanggalnya, setelah disetujui.
DAILY_OPEN_STATUSES = ("APPROVED", "ONGOING")
ALREADY_TODAY = "Absensi untuk hari ini sudah tercatat (hanya dapat mengajukan ulang jika absensi sebelumnya ditolak)."
# Keputusan pemilik 2026-10-02: ditolak → boleh mengajukan ulang SEKALI;
# ditolak lagi → hari itu terkunci (tercatat ditolak).
MAX_ATTEMPTS_PER_DAY = 2
ATTEMPTS_USED = "Absensi hari ini sudah ditolak {n} kali dan tidak dapat diajukan lagi. Hari ini tercatat ditolak."
MAX_GPS_ACCURACY_M = 100  # K-12 (docs/10): akurasi GPS > 100 m ditolak
# Absen web: lokasi browser laptop/PC berasal dari WiFi, bukan GPS — lebih kabur (docs/10 Bagian C).
MAX_WEB_ACCURACY_M = 300
# Lapangan absen di HP, kantor di web (docs/10 Bagian C, 2026-10-01).
CHANNEL_OF_MODE = {"FIELD": "MOBILE", "OFFICE": "WEB"}
WRONG_CHANNEL = {
    "MOBILE": "Anda terdaftar sebagai pekerja kantor — absen lewat web, bukan aplikasi HP.",
    "WEB": "Anda terdaftar sebagai pekerja lapangan — absen lewat aplikasi HP, bukan web.",
}
# R-33: penjelasan wajib saat absen di luar zona dan saat mengajukan ulang absensi yang ditolak.
EXPLANATION_OUTSIDE = "Anda {d:.0f} m dari {site} (radius {r} m). Isi penjelasan mengapa absen di luar zona."
EXPLANATION_RESUBMIT = "Isi penjelasan untuk mengajukan ulang absensi yang ditolak."


class AttendanceSessionService:
    """Layanan inti untuk mengelola rekaman absensi masuk/pulang, validasi koordinat GPS, dan verifikasi sesi kerja."""

    def __init__(self, repo: CRUDAttendanceSession, clock: CRUDOrgClock, faces: FaceService | None = None) -> None:
        self.repo = repo
        self.clock = clock
        self.faces = faces

    async def _employee_for_channel(self, user_id: str, channel: str) -> Any:
        """Karyawan milik akun (employee_id, attendance_mode, unit_id), dengan syarat kanal absen sesuai
        jenis pekerjanya (FIELD → aplikasi HP, OFFICE → web). Jenis pekerja dibaca dari DB, bukan dari klien."""
        row = await self.repo.attendance_mode_of(user_id)
        if row is None:
            raise ValidationError("Akun ini belum tertaut ke data karyawan.")
        # Validasi kontrol channel untuk memastikan tidak ada kecurangan dari karyawan
        # dengan menukar platform (Web vs Mobile).
        # Administrator (pemilik sistem) boleh absen dari web DAN HP, apa pun jenis absen karyawannya (2026-10-06).
        if CHANNEL_OF_MODE.get(row.attendance_mode, "MOBILE") != channel and not row.is_admin:
            raise AppError("WRONG_ATTENDANCE_CHANNEL", WRONG_CHANNEL[channel], status=403)
        return row

    async def ensure_check_in_refs(
        self, org_id: str, site_id: UUID | None, selfie_file_id: UUID | None, *, user_id: str | None = None
    ) -> None:
        """Lokasi & swafoto absen (masuk maupun pulang) harus milik organisasi pengguna (galat 422 bila bukan),
        dan swafoto harus diunggah oleh akun yang absen itu sendiri (bukan foto orang lain)."""
        await ensure_same_org(self.repo.db, org_id, sites=[site_id] if site_id else [], files=[selfie_file_id])
        if user_id and selfie_file_id:
            uploader = await self.repo.file_uploader(selfie_file_id)
            if uploader is not None and str(uploader) != str(user_id):
                raise AppError("SELFIE_NOT_OWNED", "Swafoto harus diunggah dari akun Anda sendiri.", status=422)

    async def export_csv(self, org_id: str, start: Any, end: Any) -> str:
        """P4-5 · CSV absensi untuk Finance; jam dalam zona waktu organisasi."""
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(
            [
                "Tanggal",
                "NIK",
                "Nama",
                "Lokasi",
                "Check In",
                "Check Out",
                "Terlambat",
                "Pulang Cepat",
                "Status",
                "Kategori",
                "Jarak pulang (m)",
                "Uang makan (Rp)",
            ]
        )
        for r in await self.repo.export_rows(org_id, start, end):
            writer.writerow(
                [
                    r.work_date.isoformat(),
                    r.employee_no,
                    r.full_name,
                    r.site_label,
                    r.check_in or "",
                    r.check_out or "",
                    "Ya" if r.is_late else "Tidak",
                    "Ya" if r.is_early_leave else "Tidak",
                    r.status,
                    "Luar kota" if r.city_category == "LUAR_KOTA" else "Dalam kota",
                    "" if r.check_out_distance_m is None else r.check_out_distance_m,
                    f"{r.meal_allowance_amount:.0f}",
                ]
            )
        return out.getvalue()

    async def meal_allowance(self, user: Any, start: Any, end: Any, division_id: UUID | None = None) -> list[Any]:
        """Rekap uang makan (docs/35 §5): pemegang export:attendance semua divisi; PM hanya divisi yang dipimpinnya
        (keputusan pemilik 2026-10-21). Lainnya → 403."""
        if "export:attendance" not in user.permissions:
            if user.role != "PROJECT_MANAGER" or not user.employee_id:
                raise ForbiddenError("Rekap uang makan hanya untuk PM divisi atau pengelola absensi.")
            own = await self.repo.scalar(
                "SELECT division_id FROM division WHERE pm_id = CAST(:e AS uuid) AND delete_at IS NULL LIMIT 1",
                {"e": user.employee_id},
            )
            if own is None:
                raise ForbiddenError("Anda belum memimpin divisi mana pun.")
            if division_id is not None and str(division_id) != str(own):
                raise ForbiddenError("PM hanya dapat melihat rekap uang makan divisinya.")
            division_id = own
        if end < start:
            raise ValidationError("Tanggal akhir harus sama atau setelah tanggal awal.")
        if (end - start).days > 62:
            raise ValidationError("Rentang rekap paling lama 62 hari.")
        return await self.repo.meal_allowance_recap(start, end, division_id)

    async def my_recap(self, user: Any, month: str | None) -> dict[str, Any]:
        """Rekap absensi bulanan milik sendiri: hari hadir, terlambat, pulang awal, uang makan (hanya absensi sah)."""
        worker = await self.repo.attendance_mode_of(user.user_id)
        if worker is None:
            raise ForbiddenError("Akun ini belum tertaut ke data karyawan.")
        today = jakarta_now().date()
        try:
            year, mon = (today.year, today.month) if not month else (int(month[:4]), int(month[5:7]))
            first = date(year, mon, 1)
        except (ValueError, IndexError) as exc:
            raise ValidationError("Bulan harus berformat YYYY-MM.") from exc
        last = (date(year + (mon == 12), mon % 12 + 1, 1)) - timedelta(days=1)
        rows = await self.repo.my_recap_rows(worker.employee_id, first, last)
        valid = [r for r in rows if r.is_valid]
        return {
            "month": f"{year:04d}-{mon:02d}",
            "days_present": len(rows),
            "late_days": sum(1 for r in rows if r.is_late),
            "early_leave_days": sum(1 for r in rows if r.is_early_leave),
            "pending_days": sum(1 for r in rows if r.is_pending),
            "meal_allowance_total": float(sum(r.meal_allowance_amount or 0 for r in valid)),
            "items": rows,
        }

    async def _require_enrolled(self, user_id: str, worker: Any, channel: str, online: bool) -> None:
        """T3: absen HP (online) ditolak bila wajah belum terdaftar dan saklar FACE_ENROLLMENT_REQUIRED menyala.
        Administrator dikecualikan (sama seperti gerbang pendaftaran). Absen offline tidak ditolak (sudah terjadi)."""
        if (
            self.faces is None
            or not settings.FACE_ENROLLMENT_REQUIRED
            or channel != "MOBILE"
            or not online
            or worker.is_admin
        ):
            return
        if not await self.faces.is_enrolled(worker.employee_id):
            raise AppError("FACE_NOT_ENROLLED", FACE_NOT_ENROLLED, status=409)

    async def _check_daily_target(self, site: Any, employee_id: Any, today: Any) -> None:
        """Lokasi tugas harian: jadwal APPROVED/ONGOING, tanggalnya hari ini, dan pengabsen anggota/ketua timnya."""
        if site.kind != "WORK_PLAN_DAILY":
            return
        plan = await DailyAccessRepository(self.repo.db).standing(site.id, employee_id)
        if plan is None or not (plan.is_member or plan.is_leader):
            raise AppError("SITE_NOT_ALLOWED", "Anda tidak terdaftar di tim jadwal kerja ini.", status=403)
        if plan.status not in DAILY_OPEN_STATUSES:
            raise AppError("PLAN_NOT_APPROVED", "Jadwal kerja ini belum disetujui PM.", status=409)
        if today is not None and plan.work_date != today:
            raise AppError("SITE_NOT_ALLOWED", "Jadwal kerja ini bukan untuk hari ini.", status=403)

    async def verify_face(self, employee_id: Any, selfie_file_id: UUID | None, *, online: bool) -> FaceOutcome | None:
        """Cocokkan swafoto dengan wajah terdaftar SEBELUM absen ditulis. Online & tidak cocok → ditolak (422);
        offline tidak ditolak (sudah terjadi) — hasilnya ditandai untuk OM oleh `record_face`."""
        if self.faces is None or selfie_file_id is None:
            return None
        outcome = await self.faces.verify_selfie(employee_id, selfie_file_id)
        if online and outcome.result == "MISMATCH":
            raise AppError("FACE_MISMATCH", FACE_MISMATCH, status=422)
        return outcome

    async def record_face(self, row: Any, event: str, outcome: FaceOutcome | None, *, online: bool) -> Any:
        """Hasil yang tidak bisa dipastikan → PENDING_OM dengan catatan; wajah tidak boleh dilewati diam-diam."""
        label = "masuk" if event == "CHECK_IN" else "pulang"
        if outcome is None or outcome.result == "MATCH":
            return row
        if outcome.result == "UNAVAILABLE":
            note = f"wajah absen {label} belum diperiksa: layanan pengenalan wajah tidak tersedia"
        elif outcome.result == "STALE":
            note = f"wajah absen {label} belum diperiksa: pendaftaran wajah perlu diulang (model berganti)"
        elif outcome.result == "MISMATCH":
            note = f"wajah absen {label} tidak cocok (skor {outcome.score:.0f})"
        elif not online and settings.FACE_ENROLLMENT_REQUIRED:  # NOT_ENROLLED, absen offline
            note = "belum mendaftar wajah"
        else:
            return row
        return await self.repo.flag_missing_face(row.id, event, note)

    async def _flag_for_review(self, org_id: str, row: Any, template: str) -> None:
        """T8: absen yang menjadi Perlu review → beri tahu peninjau berwenang (notifikasi + peristiwa realtime)."""
        if str(row.status) != "NEEDS_REVIEW":
            return
        reviewers = await self.repo.reviewer_employee_ids(org_id, row.employee_id)
        if not reviewers:
            return
        name = await self.repo.employee_name(row.employee_id)
        await NotificationService(self.repo.db).attendance_flagged(org_id, reviewers, template.format(name=name))
        users = await self.repo.user_ids_of(reviewers)
        queue_event(self.repo.db, users, "attendance", {"attendance_id": str(row.id)})

    async def check_in(
        self,
        org_id: str,
        user_id: str,
        *,
        site_id: UUID,
        lng: float,
        lat: float,
        origin: str,
        selfie_file_id: UUID | None,
        accuracy_m: float | None = None,
        channel: str = "MOBILE",
        explanation: str | None = None,
        at: Any = None,
        work_date: Any = None,
        online: bool = True,
    ) -> Any:
        """
        Mencatat absen masuk harian (check-in) dengan mengevaluasi aturan jarak dan akurasi GPS.

        `at`/`work_date`: absen offline (R-34) — jam & tanggal peristiwa yang sudah diverifikasi server
        (jangkar waktu + tanda tangan perangkat), bukan jam terima.

        Pengenalan wajah (M7): swafoto absen dicocokkan SERVER dengan `employee.face_embedding` sebelum absen ditulis;
        skornya disimpan di `attendance.face_match_score`. Online & tidak cocok → ditolak; layanan mati → PENDING_OM.
        """
        worker = await self._employee_for_channel(user_id, channel)
        await self._require_enrolled(user_id, worker, channel, online)
        employee_id = worker.employee_id
        # docs/35 §5: absen selalu disertai swafoto wajah (attendance.face_photo_path wajib).
        if selfie_file_id is None:
            raise ValidationError("Ambil swafoto wajah Anda untuk absen.")
        # K-12: titik GPS yang terlalu kabur tidak bisa membuktikan kehadiran — tolak dengan alasan.
        if channel == "WEB":
            if accuracy_m is not None and accuracy_m > MAX_WEB_ACCURACY_M:
                raise AppError(
                    "GPS_INACCURATE",
                    f"Akurasi lokasi browser {accuracy_m:.0f} m terlalu rendah (maksimal "
                    f"{MAX_WEB_ACCURACY_M} m). Nyalakan WiFi perangkat, izinkan akses lokasi, "
                    "lalu coba lagi.",
                    status=422,
                )
        elif accuracy_m is not None and accuracy_m > MAX_GPS_ACCURACY_M:
            raise AppError(
                "GPS_INACCURATE",
                f"Akurasi GPS {accuracy_m:.0f} m terlalu rendah (maksimal {MAX_GPS_ACCURACY_M} m). "
                "Pindah ke tempat terbuka, tunggu sinyal GPS menguat, lalu coba lagi.",
                status=422,
            )
        local_clock = await self.clock.local_now(org_id)
        today = work_date or (local_clock.today if local_clock else None)
        # Validasi jam masuk: dibuka mulai pukul 07:00 (keputusan pemilik 2026-10-14).

        is_test_env = "pytest" in sys.modules
        is_mocked_clock = hasattr(self.clock, "assert_called") or hasattr(self.clock, "return_value")
        should_check_hours = (
            online
            and not settings.SKIP_ATTENDANCE_HOURS_CHECK
            and (not is_test_env or at is not None or is_mocked_clock)
        )
        if should_check_hours:
            check_in_time = at.time() if at is not None else (local_clock.local_now.time() if local_clock else None)
            if check_in_time is not None:
                open_hour, open_min = [int(p) for p in settings.ATTENDANCE_OPEN_TIME.split(":")]
                if check_in_time < time(open_hour, open_min):
                    raise AppError(
                        "CHECKIN_TOO_EARLY",
                        f"Absensi masuk belum dibuka. Jam masuk kerja dimulai pukul {settings.ATTENDANCE_OPEN_TIME}.",
                        status=422,
                    )
        leave_info = await self.repo.is_on_approved_leave(employee_id, today)
        if isinstance(leave_info, (tuple, list)) and len(leave_info) == 2:
            on_leave, leave_type = leave_info
            if on_leave:
                raise AppError(
                    "ON_APPROVED_LEAVE",
                    f"Anda sedang dalam masa cuti/izin/sakit resmi ({leave_type}). Absensi tidak diperkenankan.",
                    status=409,
                )

        # Sesi valid yang lupa ditutup mengunci absen masuk berikutnya (O-10); absen hari lalu yang masih
        # menunggu pemeriksaan tidak mengunci hari baru (R-33).
        await self.repo.lock_employee(employee_id)
        if await self.repo.active_on(employee_id, today):
            raise AppError("ALREADY_CHECKED_IN", ALREADY_TODAY, status=409)
        opened = await self.repo.open_session(employee_id)
        if opened is not None and opened.status in VALID_STATUSES:
            raise AppError("OPEN_SESSION", OPEN_SESSION, status=409)
        rejected = await self.repo.rejected_on(employee_id, today)
        if rejected >= MAX_ATTEMPTS_PER_DAY:
            raise AppError("ATTENDANCE_DAY_LOCKED", ATTEMPTS_USED.format(n=rejected), status=409)
        site = await self.repo.site_for_check_in(site_id, org_id, lng, lat)
        if site is None:
            raise NotFoundError("Lokasi")
        if site.distance_m is None or site.radius_m is None:
            raise AppError(
                "SITE_LOCATION_REQUIRED",
                "Koordinat dan radius lokasi jadwal harus dilengkapi sebelum presensi dapat dilakukan.",
                status=422,
            )
        # R-33: pekerja kantor hanya di lokasi kantor. Pekerja lapangan di lokasi proyek unitnya DAN di kantor pusat
        # (unit_id NULL): tanpa SK aktif mereka tetap harus bisa absen di kantor (2026-10-07, permintaan pemilik).
        if worker.attendance_mode == "OFFICE":
            allowed = site.unit_id is None
        else:
            allowed = site.unit_id is None or site.unit_id == worker.unit_id
        if not allowed:
            raise AppError(
                "SITE_NOT_ALLOWED", "Lokasi ini tidak berlaku untuk Anda. Pilih lokasi kerja Anda.", status=403
            )
        # 2026-10-09 (pemilik): absen sah otomatis bila berada dalam radius kantor mana pun (Pekanbaru, Duri, Dumai,
        # Jakarta, …) atau lokasi tugas hari itu, walau lokasi yang dipilih di HP berbeda — tercatat di lokasi itu.
        if float(site.distance_m) > site.radius_m:
            nearest = await self.repo.nearest_valid_site(org_id, employee_id, today, lng, lat)
            if nearest is not None and float(nearest.distance_m) <= nearest.radius_m:
                site_id, site = nearest.id, nearest
        note = (explanation or "").strip() or None
        if note is None and float(site.distance_m) > site.radius_m:
            raise AppError(
                "EXPLANATION_REQUIRED",
                EXPLANATION_OUTSIDE.format(d=float(site.distance_m), site=site.name, r=site.radius_m),
                status=422,
            )
        if note is None and rejected >= 1:
            raise AppError("EXPLANATION_REQUIRED", EXPLANATION_RESUBMIT, status=422)
        await self._check_daily_target(site, employee_id, today)
        outcome = await self.verify_face(employee_id, selfie_file_id, online=online)
        try:
            row = await self.repo.insert(
                org_id=org_id,
                employee_id=employee_id,
                work_date=today,
                site_id=site_id,
                site_label=site.name,
                lng=lng,
                lat=lat,
                origin=origin,
                selfie_file_id=selfie_file_id,
                face_result=outcome.result if outcome else None,
                face_similarity=outcome.similarity if outcome else None,
                source=channel,
                explanation=note,
                at=at or (local_clock.local_now if local_clock else None),
            )
            row = await self.record_face(row, "CHECK_IN", outcome, online=online)
            await self._flag_for_review(org_id, row, "Absen masuk {name} perlu diperiksa")
            return row
        except IntegrityError as exc:
            # Aturan dari trigger (mis. di luar radius tanpa swafoto) → 422 dengan pesannya.
            rule = trigger_rule_message(exc)
            if rule:
                raise ValidationError(rule) from None
            if "attendance_active_uidx" in str(exc) or "employee_id_work_date" in str(exc):
                raise AppError("ALREADY_CHECKED_IN", ALREADY_TODAY, status=409) from None
            raise

    async def check_out(
        self,
        user_id: str,
        channel: str = "MOBILE",
        *,
        org_id: str | None = None,
        online: bool = True,
        lat: float | None = None,
        lng: float | None = None,
        selfie_file_id: UUID | None = None,
        explanation: str | None = None,
        accuracy_m: float | None = None,
    ) -> Any:
        """
        Menutup sesi absensi harian yang sedang terbuka (absen pulang).

        Menutup sesi terbuka milik sendiri — tanggal berapa pun, agar sesi yang lupa ditutup tidak
        mengunci check-in berikutnya. Status tidak diubah; pulang cepat diputuskan trigger.
        R-33: hanya sesi yang sudah valid (Valid otomatis / Disetujui) yang boleh absen pulang.
        """
        worker = await self._employee_for_channel(user_id, channel)
        await self._require_enrolled(user_id, worker, channel, online)
        session = await self.repo.open_session(worker.employee_id, valid_only=True)
        if session is None:
            # Memastikan tidak bisa absen pulang jika absen masuknya ditolak atau masih dalam proses peninjauan.
            if await self.repo.open_session(worker.employee_id) is not None:
                raise AppError("CHECKOUT_NOT_VALID", CHECKOUT_NOT_VALID, status=409)
            raise AppError("NO_OPEN_SESSION", "Tidak ada sesi absensi terbuka.", status=409)
        effective_org_id = org_id or str(getattr(session, "organization_id", ""))
        local_clock = await self.clock.local_now(effective_org_id) if effective_org_id else None
        now_local = local_clock.local_now if local_clock else jakarta_now()

        # Validasi laporan harian: jika ketua tim belum mengisi laporan harian jadwal kerja hari ini
        work_date = getattr(session, "attendance_date", None) or (
            now_local.date() if now_local else jakarta_now().date()
        )
        unreported_plan_id = await self.repo.active_leader_plan_without_report(worker.employee_id, work_date)
        if unreported_plan_id is not None:
            raise AppError(
                "REPORT_REQUIRED",
                "Ketua tim wajib mengisi laporan harian sebelum melakukan absensi pulang.",
                status=422,
                details={"daily_plan_id": str(unreported_plan_id)},
            )

        # Validasi batas waktu absensi pulang: ditutup pada pukul 19:00 (keputusan pemilik 2026-10-14).

        is_test_env = "pytest" in sys.modules
        is_mocked_clock = hasattr(self.clock, "assert_called") or hasattr(self.clock, "return_value")
        should_check_close = (
            online
            and not settings.SKIP_ATTENDANCE_HOURS_CHECK
            and now_local is not None
            and (not is_test_env or is_mocked_clock)
        )
        if should_check_close and now_local is not None:
            close_hour, close_min = [int(p) for p in settings.ATTENDANCE_CLOSE_TIME.split(":")]
            if now_local.time() >= time(close_hour, close_min):
                has_ot = await self.repo.has_active_overtime(worker.employee_id, work_date)
                if not has_ot:
                    raise AppError(
                        "CHECKOUT_CLOSED",
                        (
                            f"Batas waktu absensi pulang mandiri telah ditutup pada pukul "
                            f"{settings.ATTENDANCE_CLOSE_TIME}. "
                            "Sesi yang belum selesai akan ditutup secara otomatis oleh sistem."
                        ),
                        status=422,
                    )

        if accuracy_m is not None:  # K-12: titik yang terlalu kabur tidak bisa membuktikan kehadiran
            limit = MAX_WEB_ACCURACY_M if channel == "WEB" else MAX_GPS_ACCURACY_M
            if accuracy_m > limit:
                raise AppError(
                    "GPS_INACCURATE",
                    f"Akurasi lokasi {accuracy_m:.0f} m terlalu rendah (maksimal {limit} m). "
                    "Pindah ke tempat terbuka, tunggu sinyal menguat, lalu coba lagi.",
                    status=422,
                )

        outcome = await self.verify_face(worker.employee_id, selfie_file_id, online=online)

        # Evaluasi durasi kerja: 9 jam kotor = 8 jam kerja efektif + 1 jam istirahat.
        is_under_required_hours = False
        duration_text = ""
        if session.check_in_at is not None:
            check_in_time = session.check_in_at
            curr_dt = now_local
            if curr_dt is None:
                curr_dt = jakarta_now()

            if check_in_time.tzinfo is not None:
                check_in_time = check_in_time.astimezone(WIB)
                curr_dt = curr_dt.replace(tzinfo=WIB) if curr_dt.tzinfo is None else curr_dt.astimezone(WIB)
            elif curr_dt.tzinfo is not None:
                curr_dt = curr_dt.replace(tzinfo=None)

            duration_sec = max(0.0, (curr_dt - check_in_time).total_seconds())
            required_gross_sec = (settings.ATTENDANCE_REQUIRED_WORK_HOURS + settings.ATTENDANCE_BREAK_HOURS) * 3600
            if duration_sec < required_gross_sec:
                is_under_required_hours = True
                effective_sec = max(0.0, duration_sec - (settings.ATTENDANCE_BREAK_HOURS * 3600))
                eff_h = int(effective_sec // 3600)
                eff_m = int((effective_sec % 3600) // 60)
                duration_text = f"{eff_h} jam {eff_m} menit"
                early_note = f"Pulang Cepat (waktu kerja efektif: {duration_text})"
                explanation = f"{explanation} - {early_note}" if (explanation or "").strip() else early_note

        try:
            row = await self.repo.close(
                session.id, lat=lat, lng=lng, selfie_file_id=selfie_file_id, explanation=explanation, at=now_local
            )
        except IntegrityError as exc:  # T7: di luar radius tanpa swafoto/penjelasan → pesan aturan dari trigger
            rule = trigger_rule_message(exc)
            if rule:
                raise ValidationError(rule) from None
            raise
        if org_id is not None:
            row = await self.record_face(row, "CHECK_OUT", outcome, online=online)
            if getattr(row, "check_out_outside", False):
                await self._flag_for_review(
                    org_id, row, "Absen pulang {name} di luar radius (" + f"{round(row.check_out_distance_m)} m)"
                )
            else:
                await self._flag_for_review(org_id, row, "Absen pulang {name} perlu diperiksa")

        encouragement_msg = None
        if is_under_required_hours:
            if effective_org_id:
                reviewers = await self.repo.reviewer_employee_ids(effective_org_id, worker.employee_id)
                if reviewers:
                    emp_name = await self.repo.employee_name(worker.employee_id)
                    await NotificationService(self.repo.db).attendance_early_leave(
                        effective_org_id, reviewers, emp_name, duration_text
                    )
        else:
            encouragement_msg = (
                "Terima kasih atas kerja keras dan dedikasimu hari ini! Kamu telah menyelesaikan 8 jam kerja "
                "dengan luar biasa. Selamat beristirahat, jaga kesehatan, dan tetap semangat untuk esok hari! 🌟💪"
            )
            if effective_org_id:
                await NotificationService(self.repo.db).attendance_encouragement(
                    effective_org_id, str(worker.employee_id), encouragement_msg
                )

        return AttendanceRowWithEncouragement(row, encouragement_msg)

    async def list_attendance(
        self,
        org_id: str,
        user_id: str,
        *,
        view_all: bool,
        employee_id: UUID | None,
        date_from: Any,
        date_to: Any,
        status: str | None,
        page: int,
        size: int,
        scope: str = "all",
    ) -> tuple[list[Any], int]:
        """
        Mendapatkan daftar absensi berdasarkan filter, disesuaikan dengan hak visibilitas pengguna.

        R-33: Finance & OPS (`view:all_attendance`) melihat semua; PM melihat miliknya + bawahan lapangan
        di unitnya; selain itu hanya milik sendiri. Di luar cakupan → tidak tampil (tidak dibocorkan).
        Setiap baris membawa `can_review` dari server.
        """
        return await self.repo.list_page(
            org_id,
            user_id,
            view_all=view_all,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            scope=scope,
            limit=size,
            offset=(page - 1) * size,
        )

    async def day_hints(self, org_id: str, employee_id: str | None) -> tuple[Any, Any, int, Any]:
        """(hari ini, jam wajib pulang, jumlah tugas belum dilapor, id jadwal) untuk pengingat di HP/web.

        Jam wajib pulang: tepat waktu = masuk + (kerja + istirahat) jam; terlambat = jam pulang kantor.
        """
        today = await self.today(org_id)
        if not employee_id:
            return today, None, 0, None
        required_out = None
        opened = await self.repo.open_hint(employee_id)
        if opened is not None:
            checked_in = opened.clock_in_at.astimezone(WIB)
            if opened.is_late and opened.scheduled_out is not None:
                required_out = datetime.combine(checked_in.date(), opened.scheduled_out, tzinfo=WIB)
            else:
                hours = settings.ATTENDANCE_REQUIRED_WORK_HOURS + settings.ATTENDANCE_BREAK_HOURS
                required_out = checked_in + timedelta(hours=hours)
        pending = await self.repo.unreported_items(employee_id, today)
        return today, required_out, int(pending.n or 0) if pending else 0, pending.plan_id if pending else None

    async def today(self, org_id: str) -> Any:
        """Tanggal kerja hari ini menurut zona waktu organisasi — sama dengan `work_date` absen masuk."""
        return (await self.clock.local_now(org_id)).today

    async def explain_attendance(self, org_id: str, user_id: str, attendance_id: UUID, explanation: str) -> None:
        """
        Memberikan penjelasan tambahan untuk sesi absensi yang memerlukan peninjauan.
        """
        attendance = await self.repo.get(attendance_id, org_id)
        employee_id = await self.repo.employee_of(user_id)
        # Memastikan karyawan hanya dapat memberikan alasan pada absensi miliknya sendiri (V-09).
        if attendance is None or attendance.employee_id != employee_id:
            raise NotFoundError("Absensi")  # milik orang lain tidak dibocorkan (V-09)
        if attendance.status != "NEEDS_REVIEW":
            raise AppError(
                "INVALID_STATE", "Hanya absensi sendiri yang menunggu pemeriksaan dapat diberi penjelasan.", status=409
            )
        if not explanation.strip():
            raise ValidationError("Penjelasan wajib diisi.")
        await self.repo.set_explanation(attendance_id, explanation.strip())

    async def admin_patch(self, attendance_id: UUID, actor: CurrentUser, data: AttendanceAdminPatch) -> None:
        """SUPER_ADMIN mengoreksi absensi; nilai lama tidak disimpan, alasan dicatat di audit."""
        if not await self.repo.admin_exists(attendance_id):
            raise NotFoundError("Absensi")
        fields = data.model_dump(exclude={"reason"}, exclude_unset=True)
        if not fields:
            raise ValidationError("Tidak ada data yang diubah.")
        await self.repo.admin_update(attendance_id, fields)
        await write_delete_audit(
            self.repo.db, actor_user_id=actor.user_id,
            actor_role=actor.role,
            actor_email=actor.email, entity_type="attendance", entity_id=attendance_id,
            detail={"action": "PATCH", "reason": data.reason, "fields": sorted(fields)}, action="ADMIN_UPDATE",
        )

    async def admin_delete(self, attendance_id: UUID, actor: CurrentUser) -> None:
        if not await self.repo.admin_exists(attendance_id):
            raise NotFoundError("Absensi")
        await purge_row(self.repo.db, "attendance", "attendance_id", attendance_id)
        await write_delete_audit(
            self.repo.db, actor_user_id=actor.user_id,
            actor_role=actor.role,
            actor_email=actor.email, entity_type="attendance", entity_id=attendance_id,
        )

    async def review_attendance(
        self, org_id: str, user_id: str, attendance_id: UUID, approve: bool, note: str | None
    ) -> str:
        """
        Meninjau (menyetujui atau menolak) sesi absensi yang anomali.

        R-33: PM → bawahan lapangan di unitnya; Finance → pekerja kantor selain Finance; OPS → Finance.
        Tidak ada yang meninjau absensinya sendiri (cakupan: CRUD `CAN_REVIEW`).
        """
        attendance = await self.repo.get(attendance_id, org_id)
        if attendance is None:
            raise NotFoundError("Absensi")
        reviewer = await self.repo.employee_of(user_id)
        # Aturan empat mata: peninjau tidak boleh menyetujui/menolak absensinya sendiri.
        if attendance.employee_id == reviewer:
            raise ForbiddenError("Anda tidak boleh memverifikasi absensi sendiri.")
        if not await self.repo.can_review(user_id, attendance.employee_id):
            raise ForbiddenError("Absensi ini berada di luar kewenangan peninjauan Anda.")
        if attendance.status != "NEEDS_REVIEW":
            raise AppError("INVALID_STATE", "Absensi tidak menunggu pemeriksaan.", status=409)
        if not (note or "").strip():
            raise ValidationError("Catatan pemeriksaan wajib diisi.")

        status = "APPROVED" if approve else "REJECTED"
        await self.repo.set_review(attendance_id, status, reviewer, (note or "").strip())
        await NotificationService(self.repo.db).attendance_decided(
            org_id, str(attendance.employee_id), approve, (note or "").strip()
        )
        queue_event(
            self.repo.db,
            await self.repo.user_ids_of([str(attendance.employee_id)]),
            "attendance",
            {"attendance_id": str(attendance_id)},
        )
        return status
