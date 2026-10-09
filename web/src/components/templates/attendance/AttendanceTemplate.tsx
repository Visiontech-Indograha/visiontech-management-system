import type { UseQueryResult } from "@tanstack/react-query";
import { AttendanceExplainDialog } from "@/components/organisms/attendance/AttendanceExplainDialog";
import { AttendanceFilter } from "@/components/organisms/attendance/AttendanceFilter";
import { AttendanceList } from "@/components/organisms/attendance/AttendanceList";
import { AttendanceReviewDialog } from "@/components/organisms/attendance/AttendanceReviewDialog";
import { AttendanceScopeTabs } from "@/components/organisms/attendance/AttendanceScopeTabs";
import { OfficeCheckInCard } from "@/components/organisms/attendance/OfficeCheckInCard";
import type { Attendance, AttendanceFilters, AttendanceList as AttendanceListData } from "@/services/attendanceService";
import { PageTemplate } from "../PageTemplate";

type AttendanceDialog = { kind: "review" | "explain"; item: Attendance } | null;

/** Kerangka "Absensi": absen kantor, tab jenis, saringan, daftar absensi, dialog tinjau/penjelasan. */
export function AttendanceTemplate({ list, filters: f, onFilterChange: set, hasTeam, teamLabel, onScopeChange, meEmployeeId, open, onOpen, onClose }: {
  list: UseQueryResult<AttendanceListData>;
  filters: AttendanceFilters;
  onFilterChange: (patch: Partial<AttendanceFilters>) => void;
  hasTeam: boolean;
  teamLabel: string;
  onScopeChange: (scope: "mine" | "team") => void;
  meEmployeeId: string | null | undefined;
  open: AttendanceDialog;
  onOpen: (dialog: AttendanceDialog) => void;
  onClose: () => void;
}) {
  return (
    <PageTemplate title="Absensi">
      <OfficeCheckInCard />
      {hasTeam && (
        <AttendanceScopeTabs
          scope={f.scope}
          teamLabel={teamLabel}
          onScopeChange={onScopeChange}
        />
      )}
      <AttendanceFilter filters={f} onChange={set} />
      <AttendanceList list={list} page={f.page} meEmployeeId={meEmployeeId} onPageChange={(page) => set({ page })} onOpen={onOpen} />

      {open?.kind === "review" && <AttendanceReviewDialog item={open.item} onClose={onClose} />}
      {open?.kind === "explain" && <AttendanceExplainDialog item={open.item} onClose={onClose} />}
    </PageTemplate>
  );
}
