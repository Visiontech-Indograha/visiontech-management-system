import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { QueryState } from "@/components/molecules/QueryState";
import { TextField } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type Row = components["schemas"]["OvertimeRecapRow"];

const useOvertimeRecap = (month: string) =>
  useQuery({
    queryKey: ["overtime-recap", month],
    queryFn: async () => (await api.get<Row[]>("/recaps/overtime", { params: month ? { month } : {} })).data,
  });

/** "Rekap lembur" per karyawan per bulan (GET /recaps/overtime). Cakupan: Finance/OPS/Admin semua, PM unitnya. */
export function OvertimeRecapPage() {
  const [month, setMonth] = useState("");
  const recap = useOvertimeRecap(month);
  const rows = recap.data ?? [];
  return (
    <>
      <PageHeader title="Rekap lembur" />
      <div className="md:max-w-xs">
        <TextField label="Bulan" type="month" value={month} onChange={(e) => setMonth(e.target.value)} hint="Kosong = semua bulan." />
      </div>
      <QueryState query={recap} errorText="Rekap lembur tidak dapat dimuat." empty={rows.length === 0} emptyText="Belum ada lembur pada periode ini.">
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((r) => (
            <li key={`${r.employee_id}-${r.period_month}`} className="rounded-panel border border-line bg-surface p-4">
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
    </>
  );
}
