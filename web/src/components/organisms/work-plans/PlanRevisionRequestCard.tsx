import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDateTime } from "@/lib/format";
import { type Change } from "@/services/planChangeService";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Kartu mencolok: permintaan revisi ketua yang belum diputuskan PM. Tetap tampil sampai disetujui/ditolak. */
export function PlanRevisionRequestCard({ c, children }: { c: Change; children?: React.ReactNode }) {
  return (
    <div role="alert" className="rounded-panel border-2 border-warning bg-warning-bg p-4 shadow-card">
      <div className="mb-2 flex items-center justify-between gap-2">
        <TextBlock as="h3" className="text-base font-semibold text-ink">Ketua tim meminta revisi</TextBlock>
        <StatusBadge status={c.status} />
      </div>
      <TextBlock as="blockquote" className="mb-2 whitespace-pre-line rounded-control border-l-4 border-warning bg-surface px-3 py-2 text-sm text-ink">
        {c.reason}
      </TextBlock>
      <TextBlock className="text-xs text-ink">
        Diajukan oleh <TextBlock as="strong">{c.requested_by_name ?? "-"}</TextBlock> · {formatDateTime(c.created_at)}
      </TextBlock>
      {children}
    </div>
  );
}
