import type { UseQueryResult } from "@tanstack/react-query";
import { UserAvatar } from "@/components/organisms/UserAvatar";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { Pill } from "@/components/molecules/Pill";
import { PlainAction } from "@/components/molecules/PlainAction";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDate } from "@/lib/format";
import { REASON_LABEL, STATUS_LABEL, type Offboarding } from "@/services/offboardingService";
import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { useClientList } from "@/hooks/useClientList";
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
  const view = useClientList(offboardings.data, (o) => [o.employee_name, o.employee_no, o.division_name, REASON_LABEL[o.reason_type]], { prefix: "off_" });
  return (
    <QueryState
      query={offboardings}
      errorText="Daftar offboarding gagal dimuat."
      empty={(offboardings.data?.length ?? 0) === 0}
      emptyText="Belum ada proses offboarding."
      emptyAction={canManage ? <OffboardingAddButton onAdd={onAdd} /> : undefined}
    >
      <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari nama, NIP, divisi, atau alasan..." active={view.active} onReset={view.reset} />
      {view.total === 0 && <TextBlock className="rounded-panel border border-line bg-surface p-6 text-center text-mist">Tidak ada offboarding yang cocok dengan pencarian.</TextBlock>}
      <ListBlock className="space-y-2">
        {view.rows.map((o) => (
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
      {view.total > 0 && <ListPagination total={view.total} noun="offboarding" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
    </QueryState>
  );
}
