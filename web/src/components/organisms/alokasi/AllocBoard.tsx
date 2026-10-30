import type { UseQueryResult } from "@tanstack/react-query";
import { AllocMatrixGrid } from "@/components/molecules/AllocMatrixGrid";
import { QueryState } from "@/components/molecules/QueryState";
import { AllocLegend } from "./AllocLegend";
import type { WeeklyCell, WeeklyMatrix, WeeklyRow } from "@/lib/alokasi";

/** Papan alokasi: legenda + matriks, dengan status loading, error, dan kosong. */
export function AllocBoard({ query, today, selected, multi, onCell }: {
  query: UseQueryResult<WeeklyMatrix>;
  today: string;
  selected: Set<string>;
  multi: boolean;
  onCell: (row: WeeklyRow, cell: WeeklyCell) => void;
}) {
  const data = query.data;
  return (
    <div>
      <AllocLegend />
      <QueryState
        query={query}
        errorText="Alokasi mingguan belum dapat dimuat. Coba lagi."
        empty={!!data && data.rows.length === 0}
        emptyText="Belum ada tim di divisi yang Anda kelola."
      >
        {data && <AllocMatrixGrid matrix={data} today={today} selected={selected} multi={multi} onCell={onCell} />}
      </QueryState>
    </div>
  );
}
