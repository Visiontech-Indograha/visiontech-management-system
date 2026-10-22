import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { toast } from "sonner";
import { errorMessage } from "@/lib/errors";
import type { DailyFormOptions } from "@/services/dailyPlanService";
import { useExportPeriodic } from "@/services/exportService";

/** Navigasi minggu (Senin–Minggu) + filter divisi untuk halaman Jadwal harian. */
export function DailyWeekToolbar({ options, divisionId, onDivision }: {
  start: string;
  end: string;
  options: DailyFormOptions | undefined;
  divisionId: string;
  /** -7/+7 hari, atau null = minggu ini. */
  onWeek: (delta: number | null) => void;
  onDivision: (id: string) => void;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end gap-3">
      {options && options.divisions.length > 1 && (
        <div className="w-64">
          <SelectField label="Divisi" value={divisionId} onChange={(e) => onDivision(e.target.value)}>
            <ControlOption value="">Semua divisi</ControlOption>
            {options.divisions.map((d) => (
              <ControlOption key={d.division_id} value={d.division_id}>{d.name}</ControlOption>
            ))}
          </SelectField>
        </div>
      )}
    </div>
  );
}

/** Tombol persetujuan matriks: setujui semua jadwal minggu ini yang menunggu. */
export function ApproveWeekButton({ count, busy, onClick }: { count: number; busy: boolean; onClick: () => void }) {
  return (
    <ActionButton onClick={onClick} disabled={busy}>
      Setujui minggu ini ({count})
    </ActionButton>
  );
}

/** Rekap divisi minggu yang tampil (docs/35 §8): .xlsx (jadwal, BoQ, uang makan) atau slide .pptx. Butuh satu divisi. */
export function WeekRecapButtons({ divisionId, start, end }: { divisionId: string; start: string; end: string }) {
  const exporter = useExportPeriodic();
  const run = (export_format: "EXCEL_XLSX" | "PPTX") =>
    exporter.mutate(
      { division_id: divisionId, start_date: start, end_date: end, export_format },
      { onSuccess: () => toast.success("Rekap minggu berhasil dibuat."), onError: (err) => toast.error(errorMessage(err)) },
    );
  if (!divisionId) {
    return <TextBlock as="span" className="text-xs text-mist">Pilih satu divisi untuk mengunduh rekap minggu ini.</TextBlock>;
  }
  return (
    <div className="flex gap-2">
      <ActionButton variant="outline" size="sm" disabled={exporter.isPending} onClick={() => run("EXCEL_XLSX")}>
        Rekap minggu ini (.xlsx)
      </ActionButton>
      <ActionButton variant="outline" size="sm" disabled={exporter.isPending} onClick={() => run("PPTX")}>
        Laporan slide minggu ini (.pptx)
      </ActionButton>
    </div>
  );
}
