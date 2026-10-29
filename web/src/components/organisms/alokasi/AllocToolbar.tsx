import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { longDate } from "@/lib/alokasi";

/** Bilah atas Alokasi mingguan: navigasi minggu, pemilih divisi, pilih banyak, dan aksi massal. */
export function AllocToolbar(props: {
  start: string;
  end: string;
  divisions: { division_id: string; name: string }[];
  divisionId: string;
  multi: boolean;
  selectedCount: number;
  standbyCount: number;
  copyEnabled: boolean;
  onWeek: (delta: number | null) => void;
  onDivision: (id: string) => void;
  onToggleMulti: () => void;
  onClearSelection: () => void;
  onAllocate: () => void;
  onStandby: () => void;
  onCopy: () => void;
}) {
  const short = (iso: string) => longDate(iso).replace(/^\S+ /, "");
  return (
    <div className="mb-4 space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Pindah minggu">
          <ActionButton variant="outline" size="sm" onClick={() => props.onWeek(-7)} aria-label="Minggu sebelumnya">
            ‹ Sebelumnya
          </ActionButton>
          <ActionButton variant="outline" size="sm" onClick={() => props.onWeek(null)}>Hari ini</ActionButton>
          <ActionButton variant="outline" size="sm" onClick={() => props.onWeek(7)} aria-label="Minggu berikutnya">
            Berikutnya ›
          </ActionButton>
        </div>
        <TextBlock className="text-sm font-medium" aria-live="polite">
          {short(props.start)} – {short(props.end)}
        </TextBlock>
        {props.divisions.length >= 2 && (
          <div className="w-56">
            <SelectField label="Divisi" value={props.divisionId} onChange={(e) => props.onDivision(e.target.value)}>
              <ControlOption value="">Semua divisi</ControlOption>
              {props.divisions.map((d) => <ControlOption key={d.division_id} value={d.division_id}>{d.name}</ControlOption>)}
            </SelectField>
          </div>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <ActionButton variant={props.multi ? "default" : "outline"} size="sm" aria-pressed={props.multi}
                      onClick={props.onToggleMulti}>
          Pilih beberapa sel
        </ActionButton>
        {props.multi && props.selectedCount > 0 && (
          <>
            <ActionButton size="sm" onClick={props.onAllocate}>Alokasikan ({props.selectedCount})</ActionButton>
            <ActionButton variant="ghost" size="sm" onClick={props.onClearSelection}>Bersihkan pilihan</ActionButton>
          </>
        )}
        <ActionButton variant="outline" size="sm" onClick={props.onStandby} disabled={!props.standbyCount}>
          Siaga hari kosong{props.standbyCount ? ` (${props.standbyCount})` : ""}
        </ActionButton>
        <ActionButton variant="outline" size="sm" onClick={props.onCopy} disabled={!props.copyEnabled}>
          Salin minggu ke minggu berikutnya
        </ActionButton>
      </div>
    </div>
  );
}
