import type { UseQueryResult } from "@tanstack/react-query";
import { UserAvatar } from "@/components/organisms/UserAvatar";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { Pill } from "@/components/molecules/Pill";
import { PlainAction } from "@/components/molecules/PlainAction";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDate } from "@/lib/format";
import { REASON_LABEL, STATUS_LABEL, type Offboarding } from "@/services/offboardingService";
import { OffboardingAddButton } from "./OffboardingAddButton";

const TONE: Record<string, "warning" | "neutral" | "success"> = {
  CLEARANCE_PENDING: "warning",
  SUBMITTED: "neutral",
  APPROVED: "neutral",
  COMPLETED: "success",
};

/** Daftar offboarding: karyawan, alasan, tanggal efektif, status clearance/persetujuan. Klik → detail. */
export function OffboardingList({ offboardings, canManage, onAdd, onOpen }: {
  offboardings: UseQueryResult<Offboarding[]>;
  canManage: boolean;
  onAdd: () => void;
  onOpen: (id: string) => void;
}) {
  return (
    <QueryState
      query={offboardings}
      errorText="Daftar offboarding gagal dimuat."
      empty={(offboardings.data?.length ?? 0) === 0}
      emptyText="Belum ada proses offboarding."
      emptyAction={canManage ? <OffboardingAddButton onAdd={onAdd} /> : undefined}
    >
      <ListBlock className="space-y-2">
        {(offboardings.data ?? []).map((o) => (
          <ListEntry key={o.offboarding_id} className="rounded-panel border border-line bg-surface p-4 shadow-card">
            <PlainAction className="flex w-full flex-wrap items-center justify-between gap-2 text-left"
                         onClick={() => onOpen(o.offboarding_id)}>
              <UserAvatar name={o.employee_name} fileId={o.employee_photo_file_id} size="sm" />
              <div className="min-w-0 flex-1">
                <TextBlock className="font-semibold">{`${o.employee_name ?? "-"} · ${o.employee_no ?? ""}`}</TextBlock>
                <TextBlock className="text-xs text-mist">
                  {`${REASON_LABEL[o.reason_type] ?? o.reason_type} · efektif ${formatDate(o.effective_date)}`}
                  {o.division_name ? ` · ${o.division_name}` : ""}
                </TextBlock>
              </div>
              <div className="flex items-center gap-2">
                {o.pending_items > 0 && (
                  <TextBlock as="span" className="text-xs text-mist">{`${o.pending_items} barang belum kembali`}</TextBlock>
                )}
                <Pill tone={TONE[o.status] ?? "neutral"}>{STATUS_LABEL[o.status] ?? o.status}</Pill>
              </div>
            </PlainAction>
          </ListEntry>
        ))}
      </ListBlock>
    </QueryState>
  );
}
