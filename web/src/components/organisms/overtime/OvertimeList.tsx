import type { UseQueryResult } from "@tanstack/react-query";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadMoreBar } from "@/components/organisms/LoadMoreBar";
import type { KeysetMore } from "@/hooks/useKeysetList";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDate } from "@/lib/format";
import type { Overtime } from "@/services/overtimeService";

/** Daftar lembur sendiri dengan status. */
export function OvertimeList({ query, more, titled = false }: { query: UseQueryResult<Overtime[]>; more: KeysetMore; titled?: boolean }) {
  const rows = query.data ?? [];
  return (
    <section className="space-y-3">
      {titled && (
        <TextBlock as="h2" className="font-semibold text-ink">
          Lembur saya
        </TextBlock>
      )}
      <QueryState query={query} errorText="Daftar lembur tidak dapat dimuat." empty={rows.length === 0} emptyText="Belum ada pengajuan lembur.">
      <ListBlock className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {rows.map((r) => (
          <ListEntry key={r.id} className="space-y-2 rounded-panel border border-line bg-surface p-4 shadow-card">
            <div className="flex items-center justify-between gap-2">
              <TextBlock className="font-medium">{formatDate(r.work_date)}</TextBlock>
              <StatusBadge status={r.status} />
            </div>
            <TextBlock className="text-sm text-mist">
              {r.employee_name} · {r.hours} jam
            </TextBlock>
            <TextBlock className="rounded-control bg-hover p-2 text-xs">Alasan: {r.reason}</TextBlock>
            {r.review_note && <TextBlock className="text-xs text-mist">Catatan: {r.review_note}</TextBlock>}
          </ListEntry>
        ))}
      </ListBlock>
        <LoadMoreBar more={more} />
      </QueryState>
    </section>
  );
}
