import type { UseQueryResult } from "@tanstack/react-query";
import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { useClientList } from "@/hooks/useClientList";
import { QueryState } from "@/components/molecules/QueryState";
import type { AttendanceRecap } from "@/services/monitoringService";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";

type Count = "days_present" | "auto_valid" | "needs_review" | "approved" | "rejected";
const COLS: [string, Count][] = [
  ["Hadir", "days_present"],
  ["Valid otomatis", "auto_valid"],
  ["Perlu ditinjau", "needs_review"],
  ["Disetujui", "approved"],
  ["Ditolak", "rejected"],
];

/** Rekap kehadiran per karyawan (kartu di ponsel, tabel di desktop) dengan keadaan memuat/galat/kosong. */
export function AttendanceRecapSummary({ recap }: { recap: UseQueryResult<AttendanceRecap> }) {
  const rows = recap.data?.employees ?? [];
  const view = useClientList(recap.data?.employees, (r) => [r.full_name], { prefix: "abs_" });
  return (
      <QueryState
        query={recap}
        errorText="Rekap absensi tidak dapat dimuat."
        empty={rows.length === 0}
        emptyText="Belum ada data kehadiran untuk bulan ini. Pilih bulan lain di kolom Bulan."
      >
        <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari nama karyawan..." active={view.active} onReset={view.reset} />
        {view.total === 0 && <TextBlock className="mb-3 text-mist">Tidak ada yang cocok dengan pencarian.</TextBlock>}
        <ListBlock className="grid gap-3 md:hidden">
          {view.rows.map((r) => (
            <ListEntry key={r.employee_id} className="rounded-panel border border-line bg-surface shadow-card p-4">
              <TextBlock className="mb-2 font-medium">{r.full_name}</TextBlock>
              <ListBlock as="dl" className="grid grid-cols-2 gap-1 text-sm">
                {COLS.map(([label, k]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <TextBlock as="dt" className="text-mist">{label}</TextBlock>
                    <TextBlock as="dd">{r[k]}</TextBlock>
                  </div>
                ))}
              </ListBlock>
            </ListEntry>
          ))}
        </ListBlock>
        <div className="hidden overflow-x-auto rounded-panel border border-line bg-surface shadow-card md:block">
          <TableBlock className="w-full text-left text-sm">
            <TableBlockHead className="border-b border-line text-mist">
              <TableBlockRow>
                <TableBlockHeaderCell className="px-4 py-3 font-medium">Karyawan</TableBlockHeaderCell>
                {COLS.map(([label]) => (
                  <TableBlockHeaderCell key={label} className="px-4 py-3 text-right font-medium">
                    {label}
                  </TableBlockHeaderCell>
                ))}
              </TableBlockRow>
            </TableBlockHead>
            <TableBlockBody>
              {view.rows.map((r) => (
                <TableBlockRow key={r.employee_id} className="h-11 border-b border-line last:border-0">
                  <TableBlockCell className="px-4 py-2 font-medium">{r.full_name}</TableBlockCell>
                  {COLS.map(([, k]) => (
                    <TableBlockCell key={k} className="px-4 py-2 text-right">
                      {r[k]}
                    </TableBlockCell>
                  ))}
                </TableBlockRow>
              ))}
            </TableBlockBody>
          </TableBlock>
        </div>
        {view.total > 0 && <ListPagination total={view.total} noun="karyawan" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
      </QueryState>
  );
}
