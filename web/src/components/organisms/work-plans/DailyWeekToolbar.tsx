import { useState } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { toast } from "sonner";
import { errorMessage } from "@/lib/errors";
import type { DailyFormOptions } from "@/services/dailyPlanService";
import { ExportFormatButtons } from "@/components/organisms/ExportFormatButtons";
import { useExportPeriodic, useExportTeamWeek, type ExportFormat } from "@/services/exportService";

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
  if (!options || options.divisions.length <= 1) return null;
  return (
    <div className="w-full sm:w-56 [&>div]:mb-0">
      <SelectField label="Divisi" value={divisionId} onChange={(e) => onDivision(e.target.value)}>
        <ControlOption value="">Semua divisi</ControlOption>
        {options.divisions.map((d) => (
          <ControlOption key={d.division_id} value={d.division_id}>{d.name}</ControlOption>
        ))}
      </SelectField>
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

/** Laporan mingguan tim (PDF, Word, atau PowerPoint) untuk satu tim pada minggu yang tampil (API /exports/team-week). */
export function TeamWeekButton({ teams, start }: { teams: DailyFormOptions["teams"]; start: string }) {
  const exporter = useExportTeamWeek();
  const [picked, setPicked] = useState("");
  const teamId = picked || (teams.length === 1 ? teams[0]!.team_id : "");
  const run = (export_format: ExportFormat) =>
    exporter.mutate(
      { team_id: teamId, start_date: start, export_format },
      { onSuccess: () => toast.success("Laporan mingguan tim berhasil dibuat."), onError: (err) => toast.error(errorMessage(err)) },
    );
  return (
    <div className="flex flex-wrap items-end gap-2">
      {teams.length > 1 && (
        <div className="w-full sm:w-52 [&>div]:mb-0">
          <SelectField label="Tim" value={teamId} onChange={(e) => setPicked(e.target.value)}>
            <ControlOption value="">Pilih tim</ControlOption>
            {teams.map((t) => (
              <ControlOption key={t.team_id} value={t.team_id}>{t.name}</ControlOption>
            ))}
          </SelectField>
        </div>
      )}
      <ExportFormatButtons
        label="Laporan mingguan tim"
        busy={exporter.isPending}
        pendingFormat={exporter.variables?.export_format}
        disabled={!teamId}
        onPick={run}
      />
    </div>
  );
}

/** Rekap divisi minggu yang tampil (docs/35 §8): .xlsx (jadwal, BoQ, uang makan) atau slide .pptx. Butuh satu divisi. */
export function WeekRecapButtons({
  divisionId,
  start,
  end,
  onOpenPresentation,
}: {
  divisionId: string;
  start: string;
  end: string;
  onOpenPresentation?: () => void;
}) {
  const exporter = useExportPeriodic();
  const run = (export_format: "EXCEL_XLSX" | "PPTX") =>
    exporter.mutate(
      { division_id: divisionId, start_date: start, end_date: end, export_format },
      { onSuccess: () => toast.success("Rekap minggu berhasil dibuat."), onError: (err) => toast.error(errorMessage(err)) },
    );
  return (
    <div className="flex flex-wrap items-center gap-2">
      {divisionId ? (
        <>
          <ActionButton variant="outline" size="sm" className="h-10" disabled={exporter.isPending} onClick={() => run("EXCEL_XLSX")}>
            Rekap minggu ini (.xlsx)
          </ActionButton>
          <ActionButton variant="outline" size="sm" className="h-10" disabled={exporter.isPending} onClick={() => run("PPTX")}>
            Laporan slide minggu ini (.pptx)
          </ActionButton>
        </>
      ) : (
        <TextBlock as="span" className="text-xs text-mist">Pilih satu divisi untuk mengunduh rekap minggu ini.</TextBlock>
      )}
      {onOpenPresentation && (
        <ActionButton variant="secondary" size="sm" className="h-10" onClick={onOpenPresentation}>
          Presentasi Evaluasi Sabtu
        </ActionButton>
      )}
    </div>
  );
}
