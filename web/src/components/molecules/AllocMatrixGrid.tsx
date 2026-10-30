import { Button } from "../atoms/Button";
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "../atoms/Table";
import { Text } from "../atoms/Text";
import { cn } from "@/lib/utils";
import {
  CELL_LABEL,
  CELL_TONE,
  DAY_LABEL,
  cellKind,
  longDate,
  type WeeklyCell,
  type WeeklyMatrix,
  type WeeklyRow,
} from "@/lib/alokasi";

/**
 * Tabel tim (baris) × hari Senin–Minggu (kolom). Setiap sel adalah tombol: label status ditulis di dalam sel,
 * sehingga warna bukan satu-satunya pembeda. Sel kosong masa depan bisa dipilih.
 */
export function AllocMatrixGrid({ matrix, today, selected, multi, onCell }: {
  matrix: WeeklyMatrix;
  today: string;
  selected: Set<string>;
  multi: boolean;
  onCell: (row: WeeklyRow, cell: WeeklyCell) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <Table aria-label="Matriks alokasi mingguan" className="min-w-[680px] border-separate border-spacing-1 text-sm">
        <TableHead>
          <TableRow>
            <TableHeaderCell scope="col" className="w-48 px-2 py-1 text-left font-medium">Tim</TableHeaderCell>
            {matrix.days.map((day, i) => (
              <TableHeaderCell scope="col" key={day}
                               className={cn("px-1 py-1 text-center font-medium", day === today && "text-brand-700")}>
                {DAY_LABEL[i]} {Number(day.slice(8))}
              </TableHeaderCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {matrix.rows.map((row) => (
            <TableRow key={row.team_id}>
              <TableHeaderCell scope="row" className="px-2 py-1 text-left align-top font-medium">
                {row.team_name}
                <Text className="text-xs font-normal text-neutral-500">{row.leader_name ?? "Tanpa ketua"}</Text>
              </TableHeaderCell>
              {row.cells.map((cell) => {
                const kind = cellKind(cell);
                const isSel = selected.has(`${row.team_id}|${cell.work_date}`);
                const bookable = kind === "EMPTY" && cell.work_date >= today;
                const label = `${row.team_name}, ${longDate(cell.work_date)}: ${CELL_LABEL[kind]}${kind !== "EMPTY" && cell.item_count ? `, ${cell.item_count} item` : ""}`;
                return (
                  <TableCell key={cell.work_date} className="p-0">
                    <Button
                      type="button"
                      variant="ghost"
                      aria-label={isSel ? `${label}, dipilih` : label}
                      aria-pressed={multi && bookable ? isSel : undefined}
                      disabled={kind === "EMPTY" && !bookable}
                      onClick={() => onCell(row, cell)}
                      className={cn(
                        "flex h-auto min-h-14 w-full flex-col items-center justify-center whitespace-normal rounded-md border px-1 py-1 text-xs font-normal",
                        "disabled:cursor-default disabled:opacity-60",
                        CELL_TONE[kind],
                        isSel && "ring-2 ring-brand-500",
                      )}
                    >
                      <Text as="span" className="font-medium">{CELL_LABEL[kind]}</Text>
                      {kind !== "EMPTY" && cell.item_count > 0 && <Text as="span">{cell.item_count} item</Text>}
                    </Button>
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
