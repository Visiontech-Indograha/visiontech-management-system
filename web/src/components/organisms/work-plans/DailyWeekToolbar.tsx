import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDate } from "@/lib/format";
import type { DailyFormOptions } from "@/services/dailyPlanService";

/** Navigasi minggu (Senin–Minggu) + filter divisi untuk halaman Jadwal harian. */
export function DailyWeekToolbar({ start, end, options, divisionId, onWeek, onDivision }: {
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
      <div className="flex items-center gap-2">
        <ActionButton variant="outline" size="sm" aria-label="Minggu sebelumnya" onClick={() => onWeek(-7)}>‹</ActionButton>
        <ActionButton variant="outline" size="sm" onClick={() => onWeek(null)}>Minggu ini</ActionButton>
        <ActionButton variant="outline" size="sm" aria-label="Minggu berikutnya" onClick={() => onWeek(7)}>›</ActionButton>
        <TextBlock as="span" className="ml-2 font-medium">{formatDate(start)} – {formatDate(end)}</TextBlock>
      </div>
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
