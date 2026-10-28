import type { UseQueryResult } from "@tanstack/react-query";
import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { useClientList } from "@/hooks/useClientList";
import { QueryState } from "@/components/molecules/QueryState";
import type { OvertimeRecapRow } from "@/services/monitoringService";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

/** Kartu rekap lembur per karyawan per bulan, dengan keadaan memuat/galat/kosong. */
export function OvertimeRecapList({ query }: { query: UseQueryResult<OvertimeRecapRow[]> }) {
  const rows = query.data ?? [];
  const view = useClientList(query.data, (r) => [r.employee_name, r.period_month], { prefix: "lbr_" });
  return (
    <QueryState query={query} errorText="Rekap lembur tidak dapat dimuat." empty={rows.length === 0} emptyText="Belum ada lembur pada periode ini.">
      <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari nama karyawan atau bulan..." active={view.active} onReset={view.reset} />
      {view.total === 0 && <TextBlock className="mb-3 text-mist">Tidak ada yang cocok dengan pencarian.</TextBlock>}
      <ListBlock className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {view.rows.map((r) => (
          <ListEntry key={`${r.employee_id}-${r.period_month}`} className="rounded-panel border border-line bg-surface shadow-card p-4">
            <TextBlock className="font-medium">{r.employee_name}</TextBlock>
            <TextBlock className="mb-2 text-sm text-mist">{r.period_month ? r.period_month.slice(0, 7) : "-"}</TextBlock>
            <ListBlock as="dl" className="grid grid-cols-3 gap-2 text-sm">
              <div>
                <TextBlock as="dt" className="text-mist">Jam disetujui</TextBlock>
                <TextBlock as="dd" className="font-medium">{r.approved_hours}</TextBlock>
              </div>
              <div>
                <TextBlock as="dt" className="text-mist">Disetujui</TextBlock>
                <TextBlock as="dd">{r.approved_entries}</TextBlock>
              </div>
              <div>
                <TextBlock as="dt" className="text-mist">Menunggu</TextBlock>
                <TextBlock as="dd">{r.pending_entries}</TextBlock>
              </div>
            </ListBlock>
          </ListEntry>
        ))}
      </ListBlock>
      {view.total > 0 && <ListPagination total={view.total} noun="karyawan" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
    </QueryState>
  );
}
