import type { UseQueryResult } from "@tanstack/react-query";
import { QueryState } from "@/components/molecules/QueryState";
import type { AttendanceRecap } from "@/services/monitoringService";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";

type Count = "days_present" | "auto_valid" | "needs_review" | "approved" | "rejected";
const COLS: [string, Count][] = [
  ["Hadir", "days_present"],
  ["Valid otomatis", "auto_valid"],
  ["Perlu review", "needs_review"],
  ["Disetujui", "approved"],
  ["Ditolak", "rejected"],
];

/** Rekap kehadiran per karyawan (kartu di ponsel, tabel di desktop) dengan keadaan memuat/galat/kosong. */
export function AttendanceRecapSummary({ recap }: { recap: UseQueryResult<AttendanceRecap> }) {
  const rows = recap.data?.employees ?? [];
  return (
      <QueryState
        query={recap}
        errorText="Rekap absensi tidak dapat dimuat."
        empty={rows.length === 0}
        emptyText="Belum ada catatan kehadiran pada bulan ini."
      >
        <ListBlock className="grid gap-3 md:hidden">
          {rows.map((r) => (
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
              {rows.map((r) => (
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
      </QueryState>
  );
}
