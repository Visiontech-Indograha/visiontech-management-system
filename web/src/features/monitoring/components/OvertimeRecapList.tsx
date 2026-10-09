import type { UseQueryResult } from "@tanstack/react-query";
import { QueryState } from "@/components/molecules/QueryState";
import type { OvertimeRecapRow } from "../monitoringService";

/** Kartu rekap lembur per karyawan per bulan, dengan keadaan memuat/galat/kosong. */
export function OvertimeRecapList({ query }: { query: UseQueryResult<OvertimeRecapRow[]> }) {
  const rows = query.data ?? [];
  return (
    <QueryState query={query} errorText="Rekap lembur tidak dapat dimuat." empty={rows.length === 0} emptyText="Belum ada lembur pada periode ini.">
      <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {rows.map((r) => (
          <li key={`${r.employee_id}-${r.period_month}`} className="rounded-panel border border-line bg-surface shadow-card p-4">
            <p className="font-medium">{r.employee_name}</p>
            <p className="mb-2 text-sm text-mist">{r.period_month.slice(0, 7)}</p>
            <dl className="grid grid-cols-3 gap-2 text-sm">
              <div>
                <dt className="text-mist">Jam disetujui</dt>
                <dd className="font-medium">{r.approved_hours}</dd>
              </div>
              <div>
                <dt className="text-mist">Disetujui</dt>
                <dd>{r.approved_entries}</dd>
              </div>
              <div>
                <dt className="text-mist">Menunggu</dt>
                <dd>{r.pending_entries}</dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </QueryState>
  );
}
