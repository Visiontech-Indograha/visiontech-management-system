import type { UseQueryResult } from "@tanstack/react-query";
import { AttendanceExplainDialog } from "@/components/organisms/attendance/AttendanceExplainDialog";
import { AttendanceExportPanel } from "@/components/organisms/attendance/AttendanceExportPanel";
import { AttendanceFilter } from "@/components/organisms/attendance/AttendanceFilter";
import { AttendanceList } from "@/components/organisms/attendance/AttendanceList";
import { AttendanceReviewDialog } from "@/components/organisms/attendance/AttendanceReviewDialog";
import { AttendanceScopeTabs } from "@/components/organisms/attendance/AttendanceScopeTabs";
import { OfficeCheckInCard } from "@/components/organisms/attendance/OfficeCheckInCard";
import type { KeysetMore } from "@/hooks/useKeysetList";
import type { Attendance,AttendanceFilters, AttendanceList as AttendanceListData } from "@/services/attendanceService";
import { PageTemplate } from "../PageTemplate";

type AttendanceDialog = { kind: "review" | "explain"; item: Attendance } | null;

/** Kerangka "Absensi": absen kantor, tab jenis, saringan, daftar absensi, dialog tinjau/penjelasan. */
export function AttendanceTemplate({ list, more, filters: f, onFilterChange: set, hasTeam, teamLabel, onScopeChange, meEmployeeId, canExport, open, onOpen, onClose }: {
  list: UseQueryResult<AttendanceListData>;
  more: KeysetMore;
  filters: AttendanceFilters;
  onFilterChange: (patch: Partial<AttendanceFilters>) => void;
  hasTeam: boolean;
  teamLabel: string;
  onScopeChange: (scope: "mine" | "team") => void;
  meEmployeeId: string | null | undefined;
  canExport: boolean;
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
      {canExport && <AttendanceExportPanel />}
      <AttendanceList
        list={list}
        more={more}
        meEmployeeId={meEmployeeId}
        onOpen={onOpen}
        emptyText={f.scope === "team" && f.status === "NEEDS_REVIEW" ? "Tidak ada absen yang perlu Anda tinjau. Absen Anda sendiri ditinjau oleh atasan." : undefined}
      />

      {open?.kind === "review" && <AttendanceReviewDialog item={open.item} onClose={onClose} />}
      {open?.kind === "explain" && <AttendanceExplainDialog item={open.item} onClose={onClose} />}
    </PageTemplate>
  );
}
