import { useState } from "react";
import { useSession } from "@/stores/sessionStore";
import { AttendanceTemplate } from "@/components/templates/attendance/AttendanceTemplate";
import { useAttendance, type Attendance, type AttendanceFilters } from "@/services/attendanceService";

/**
 * Daftar absensi (GET /attendance) — prototype/js/operations.js attendance(). Cakupan data diatur API (R-33):
 * Finance & OPS seluruh organisasi; PM miliknya + bawahan lapangan di unitnya; lainnya milik sendiri.
 * Tombol Tinjau hanya bila server menandai `can_review` (PM → bawahan, Finance → kantor, OPS → Finance).
 * Absen masuk/pulang: pekerja kantor di sini (OfficeCheckInCard), pekerja lapangan di aplikasi HP.
 */
export function AttendancePage() {
  const { me } = useSession();
  const canReview = !!me?.permissions.includes("review:attendance");
  // Pemegang wewenang lihat/tinjau absensi orang lain: pisahkan absensi pribadi dari absensi anggota (PM) / umum (Finance, OPS).
  const sees = !!me?.permissions.includes("view:all_attendance");
  const hasTeam = canReview || sees;
  const teamLabel = sees ? "Semua karyawan" : "Absensi anggota";
  const [f, setF] = useState<AttendanceFilters>({
    status: canReview ? "NEEDS_REVIEW" : "", from: "", to: "", q: "", page: 1, scope: hasTeam ? "team" : "",
  });
  const list = useAttendance(f);
  const [open, setOpen] = useState<{ kind: "review" | "explain"; item: Attendance } | null>(null);
  const set = (patch: Partial<AttendanceFilters>) => setF((old) => ({ ...old, ...patch, page: patch.page ?? 1 }));

  return (
    <AttendanceTemplate
      list={list}
      filters={f}
      onFilterChange={set}
      hasTeam={hasTeam}
      teamLabel={teamLabel}
      onScopeChange={(key) => setF((old) => ({ ...old, scope: key, status: key === "team" && canReview ? "NEEDS_REVIEW" : "", page: 1 }))}
      meEmployeeId={me?.employee_id}
      canExport={!!me?.permissions.includes("export:attendance")}
      open={open}
      onOpen={setOpen}
      onClose={() => setOpen(null)}
    />
  );
}
