import { useState } from "react";
import { useSession } from "@/app/session";
import { AttendanceExplainDialog } from "@/components/organisms/attendance/AttendanceExplainDialog";
import { AttendanceFilter } from "@/components/organisms/attendance/AttendanceFilter";
import { AttendanceList } from "@/components/organisms/attendance/AttendanceList";
import { AttendanceReviewDialog } from "@/components/organisms/attendance/AttendanceReviewDialog";
import { AttendanceScopeTabs } from "@/components/organisms/attendance/AttendanceScopeTabs";
import { OfficeCheckInCard } from "@/components/organisms/attendance/OfficeCheckInCard";
import { PageTemplate } from "@/components/templates/PageTemplate";
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
  const teamLabel = sees ? "Absensi umum" : "Absensi anggota";
  const [f, setF] = useState<AttendanceFilters>({
    status: canReview ? "NEEDS_REVIEW" : "", from: "", to: "", page: 1, scope: hasTeam ? "team" : "",
  });
  const list = useAttendance(f);
  const [open, setOpen] = useState<{ kind: "review" | "explain"; item: Attendance } | null>(null);
  const set = (patch: Partial<AttendanceFilters>) => setF((old) => ({ ...old, ...patch, page: patch.page ?? 1 }));

  return (
    <PageTemplate title="Absensi">
      <OfficeCheckInCard />
      {hasTeam && (
        <AttendanceScopeTabs
          scope={f.scope}
          teamLabel={teamLabel}
          onScopeChange={(key) => setF((old) => ({ ...old, scope: key, status: key === "team" && canReview ? "NEEDS_REVIEW" : "", page: 1 }))}
        />
      )}
      <AttendanceFilter filters={f} onChange={set} />
      <AttendanceList list={list} page={f.page} meEmployeeId={me?.employee_id} onPageChange={(page) => set({ page })} onOpen={setOpen} />

      {open?.kind === "review" && <AttendanceReviewDialog item={open.item} onClose={() => setOpen(null)} />}
      {open?.kind === "explain" && <AttendanceExplainDialog item={open.item} onClose={() => setOpen(null)} />}
    </PageTemplate>
  );
}
