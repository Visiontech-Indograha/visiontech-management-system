import type { UseQueryResult } from "@tanstack/react-query";
import { formatDate } from "@/lib/format";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { Calendar, CheckCircle2, Clock, XCircle } from "@/components/molecules/Glyphs";
import { LeaveApplyButton } from "./LeaveApplyButton";
import { LEAVE_TYPE_LABEL, type LeaveRequest } from "@/services/leaveService";

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  PENDING: { label: "Menunggu Persetujuan", className: "bg-amber-500/15 text-amber-600 font-medium" },
  APPROVED_BY_PM: { label: "Disetujui PM", className: "bg-leaf/15 text-leaf font-medium" },
  APPROVED_BY_HR: { label: "Disetujui HR", className: "bg-leaf/15 text-leaf font-medium" },
  APPROVED_BY_FINANCE: { label: "Disetujui Finance", className: "bg-leaf/15 text-leaf font-medium" },
  REJECTED: { label: "Ditolak", className: "bg-danger/15 text-danger font-medium" },
  CANCELLED: { label: "Dibatalkan", className: "bg-hover text-mist font-medium" },
};

export function LeaveList({
  leaves,
  statusFilter,
  onStatusFilterChange,
  canReview,
  canFinalReview,
  onApply,
  onReview,
}: {
  leaves: UseQueryResult<LeaveRequest[]>;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  canReview: boolean;
  canFinalReview: boolean;
  onApply: () => void;
  onReview: (leave: LeaveRequest) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="w-full sm:w-60">
          <SelectField
            label=""
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value)}
          >
            <ControlOption value="">-- Semua Status --</ControlOption>
            <ControlOption value="PENDING">Menunggu Persetujuan</ControlOption>
            <ControlOption value="APPROVED_BY_PM">Disetujui PM</ControlOption>
            <ControlOption value="APPROVED_BY_HR">Disetujui HR</ControlOption>
            <ControlOption value="REJECTED">Ditolak</ControlOption>
            <ControlOption value="CANCELLED">Dibatalkan</ControlOption>
          </SelectField>
        </div>
      </div>

      {leaves.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <LoadingBar className="h-28" />
          <LoadingBar className="h-28" />
        </div>
      )}

      {leaves.isError && (
        <RetryNotice
          message="Riwayat permohonan cuti tidak dapat dimuat."
          onRetry={() => leaves.refetch()}
        />
      )}

      {leaves.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface p-8 text-center shadow-card">
          <Calendar className="mx-auto mb-3 text-mist" size={36} />
          <TextBlock className="mb-2 font-medium">Belum ada riwayat permohonan cuti</TextBlock>
          <TextBlock className="mb-4 text-sm text-mist">
            {statusFilter
              ? "Tidak ada permohonan cuti dengan status ini."
              : "Ajukan permohonan cuti tahunan atau izin sakit saat berhalangan hadir."}
          </TextBlock>
          {!statusFilter && <LeaveApplyButton onApply={onApply} />}
        </div>
      )}

      {leaves.data && leaves.data.length > 0 && (
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {leaves.data.map((l) => {
            const statusBadge = STATUS_BADGE[l.status] ?? {
              label: l.status,
              className: "bg-hover text-mist",
            };
            const isPending = l.status === "PENDING";

            return (
              <ListEntry
                key={l.leave_id}
                className="flex flex-col justify-between rounded-panel border border-line bg-surface p-4 shadow-card hover:border-mist transition-colors"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <TextBlock as="span" className="rounded-control bg-hover px-2 py-0.5 text-xs font-semibold text-foreground">
                          {LEAVE_TYPE_LABEL[l.leave_type] ?? l.leave_type}
                        </TextBlock>
                        <TextBlock as="span" className={`rounded-control px-2 py-0.5 text-xs ${statusBadge.className}`}>
                          {statusBadge.label}
                        </TextBlock>
                      </div>
                      <TextBlock className="font-semibold text-foreground mt-1.5">{l.employee_name}</TextBlock>
                      {l.division_name && (
                        <TextBlock as="span" className="text-xs text-mist">{l.division_name}</TextBlock>
                      )}
                    </div>
                  </div>

                  <div className="space-y-1 my-2 text-xs text-mist">
                    <div className="flex items-center gap-1.5">
                      <Clock size={13} className="shrink-0" />
                      <TextBlock as="span">
                        {formatDate(String(l.start_date))} s/d {formatDate(String(l.end_date))} (
                        <TextBlock as="strong" className="text-foreground">{l.total_days} hari</TextBlock>)
                      </TextBlock>
                    </div>
                    <div className="p-2 rounded-control bg-hover text-xs text-foreground mt-2">
                      <TextBlock as="span" className="text-mist block text-[11px] mb-0.5">Alasan:</TextBlock>
                      <TextBlock as="span">{l.reason}</TextBlock>
                    </div>
                  </div>

                  {l.rejection_note && (
                    <div className="mt-2 p-2 rounded-control bg-danger/10 text-xs text-danger flex items-start gap-1.5">
                      <XCircle size={14} className="shrink-0 mt-0.5" />
                      <TextBlock as="span">Catatan Penolakan: {l.rejection_note}</TextBlock>
                    </div>
                  )}

                  {l.reviewed_by_name && (
                    <div className="mt-2 text-[11px] text-mist flex items-center gap-1">
                      <CheckCircle2 size={12} className="text-leaf" />
                      <TextBlock as="span">
                        Ditinjau oleh {l.reviewed_by_name} ({String(l.reviewed_at ?? "").slice(0, 10)})
                      </TextBlock>
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-line flex items-center justify-between text-xs">
                  <TextBlock as="span" className="text-mist">
                    Diajukan {formatDate(String(l.create_at))}
                  </TextBlock>
                  {canReview && (isPending || (canFinalReview && l.status === "APPROVED_BY_PM")) && (
                    <ActionButton
                      variant="outline"
                      size="sm"
                      onClick={() => onReview(l)}
                      aria-label={`Tinjau cuti ${l.employee_name}`}
                    >
                      Tinjau Permohonan
                    </ActionButton>
                  )}
                </div>
              </ListEntry>
            );
          })}
        </ListBlock>
      )}
    </div>
  );
}
