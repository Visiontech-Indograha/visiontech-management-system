import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { Trash2 } from "@/components/molecules/Glyphs";
import { Pill } from "@/components/molecules/Pill";
import {
  TableBlock,
  TableBlockBody,
  TableBlockCell,
  TableBlockHead,
  TableBlockHeaderCell,
  TableBlockRow,
} from "@/components/molecules/TableBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { SURVEY_UNITS, useSurveyBom, type Survey, type SurveyLine } from "@/services/surveyService";

const num = (v: string | number) => {
  const n = Number(v);
  return Number.isInteger(n) ? String(n) : String(n).replace(".", ",");
};

/** Ringkasan BoM per kelompok (jenis titik / Umum) — sama dengan tabel BoM di laporan. */
function BomSummary({ survey }: { survey: Survey }) {
  return (
    <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
      <TableBlock className="w-full text-left text-sm">
        <TableBlockHead className="border-b border-line text-mist">
          <TableBlockRow>
            <TableBlockHeaderCell className="px-4 py-3 font-medium">No</TableBlockHeaderCell>
            <TableBlockHeaderCell className="px-4 py-3 font-medium">Nama material</TableBlockHeaderCell>
            <TableBlockHeaderCell className="px-4 py-3 text-right font-medium">Qty</TableBlockHeaderCell>
            <TableBlockHeaderCell className="px-4 py-3 font-medium">Satuan</TableBlockHeaderCell>
          </TableBlockRow>
        </TableBlockHead>
        <TableBlockBody>
          {survey.bom.map((b, i) => {
            const header = i === 0 || survey.bom[i - 1].group !== b.group;
            return [
              header && (
                <TableBlockRow key={`g-${b.group}`} className="border-b border-line bg-hover">
                  <TableBlockCell colSpan={4} className="px-4 py-2 text-xs font-semibold uppercase text-mist">
                    {b.group}
                  </TableBlockCell>
                </TableBlockRow>
              ),
              <TableBlockRow key={`${b.group}-${b.name}-${b.unit}`} className="border-b border-line last:border-0">
                <TableBlockCell className="px-4 py-2">{i + 1}</TableBlockCell>
                <TableBlockCell className="px-4 py-2">
                  {b.name} {b.custom && <Pill tone="warning">di luar katalog</Pill>}
                </TableBlockCell>
                <TableBlockCell className="px-4 py-2 text-right">{num(b.qty)}</TableBlockCell>
                <TableBlockCell className="px-4 py-2">{b.unit}</TableBlockCell>
              </TableBlockRow>,
            ];
          })}
        </TableBlockBody>
      </TableBlock>
    </div>
  );
}

/** Satu baris yang bisa diubah: jumlah (dan satuan untuk material di luar katalog), hapus, simpan ke katalog. */
function LineEditor({ survey, line, pointTypeId }: { survey: Survey; line: SurveyLine; pointTypeId: string | null }) {
  const bom = useSurveyBom(survey.task_id);
  const [qty, setQty] = useState(String(Number(line.qty)));
  const [unit, setUnit] = useState(line.unit);
  const changed = Number(qty) !== Number(line.qty) || unit !== line.unit;
  const busy = bom.edit.isPending || bom.remove.isPending || bom.toCatalog.isPending;
  const run = async (p: Promise<unknown>, ok: string) => {
    try {
      await p;
      toast.success(ok);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <div className="flex flex-wrap items-end gap-2 border-b border-line py-2 last:border-0">
      <div className="min-w-40 flex-1">
        <TextBlock className="text-sm">{line.name}</TextBlock>
        {line.custom && <Pill tone="warning">di luar katalog</Pill>}
      </div>
      <TextField label="Qty" type="number" min={0} step="any" className="w-24" value={qty} onChange={(e) => setQty(e.target.value)} />
      {line.custom ? (
        <SelectField label="Satuan" value={unit} onChange={(e) => setUnit(e.target.value)}>
          {[...new Set([...SURVEY_UNITS, line.unit])].map((u) => (
            <ControlOption key={u} value={u}>{u}</ControlOption>
          ))}
        </SelectField>
      ) : (
        <TextBlock className="pb-2 text-sm text-mist">{line.unit}</TextBlock>
      )}
      <ActionButton
        size="sm"
        disabled={!changed || busy || !(Number(qty) >= 0)}
        onClick={() => void run(bom.edit.mutateAsync({ bomId: line.bom_id, name: line.name, qty: Number(qty), unit }), "Material disimpan.")}
      >
        Simpan
      </ActionButton>
      {line.custom && pointTypeId && survey.can_review && (
        <ActionButton
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={() =>
            void run(bom.toCatalog.mutateAsync({ point_type_id: pointTypeId, name: line.name, unit }), "Disimpan ke katalog.")
          }
        >
          Simpan ke katalog
        </ActionButton>
      )}
      <ActionButton
        size="sm"
        variant="ghost"
        aria-label={`Hapus ${line.name}`}
        disabled={busy}
        onClick={() => void run(bom.remove.mutateAsync(line.bom_id), "Material dihapus.")}
      >
        <Trash2 className="h-4 w-4" />
      </ActionButton>
    </div>
  );
}

/** Tambah material umum lokasi (rack, panel, kabel tray utama, …) — satuan dipilih dari daftar baku. */
function AddGeneralLine({ survey }: { survey: Survey }) {
  const bom = useSurveyBom(survey.task_id);
  const [name, setName] = useState("");
  const [qty, setQty] = useState("1");
  const [unit, setUnit] = useState<string>(SURVEY_UNITS[0]);
  return (
    <FormBlock
      className="flex flex-wrap items-end gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!name.trim() || !(Number(qty) > 0)) return toast.error("Isi nama material dan jumlahnya.");
        try {
          await bom.add.mutateAsync({ name: name.trim(), qty: Number(qty), unit });
          setName("");
          setQty("1");
          toast.success("Material umum ditambahkan.");
        } catch (err) {
          toast.error(errorMessage(err));
        }
      }}
    >
      <TextField label="Material umum lokasi" placeholder="mis. Rack 19 inch" value={name} onChange={(e) => setName(e.target.value)} />
      <TextField label="Qty" type="number" min={0} step="any" className="w-24" value={qty} onChange={(e) => setQty(e.target.value)} />
      <SelectField label="Satuan" value={unit} onChange={(e) => setUnit(e.target.value)}>
        {SURVEY_UNITS.map((u) => (
          <ControlOption key={u} value={u}>{u}</ControlOption>
        ))}
      </SelectField>
      <ActionButton type="submit" size="sm" disabled={bom.add.isPending}>Tambah</ActionButton>
    </FormBlock>
  );
}

/** Bill of Material survei: ringkasan per jenis titik + umum; PM (saat meninjau) atau ketua tim (draf) bisa mengubah. */
export function SurveyBomPanel({ survey }: { survey: Survey }) {
  const empty = survey.bom.length === 0;
  return (
    <section aria-label="Daftar material" className="space-y-4">
      {empty ? (
        <TextBlock className="text-sm text-mist">Belum ada material yang dicatat di titik survei.</TextBlock>
      ) : (
        <BomSummary survey={survey} />
      )}
      {survey.can_edit_bom && (
        <div className="space-y-4 rounded-panel border border-line bg-surface p-4 shadow-card">
          <TextBlock className="text-sm font-medium">
            Sesuaikan BoM sebelum disetujui — setiap perubahan tercatat di riwayat.
          </TextBlock>
          {survey.points.map((p) =>
            p.lines.some((l) => l.category === "MATERIAL") ? (
              <div key={p.point_id}>
                <TextBlock className="text-xs font-semibold uppercase text-mist">{`${p.name} · ${p.point_type_name}`}</TextBlock>
                {p.lines
                  .filter((l) => l.category === "MATERIAL")
                  .map((l) => (
                    <LineEditor key={l.bom_id} survey={survey} line={l} pointTypeId={p.point_type_id} />
                  ))}
              </div>
            ) : null,
          )}
          <div>
            <TextBlock className="text-xs font-semibold uppercase text-mist">Umum</TextBlock>
            {survey.general_lines.map((l) => (
              <LineEditor key={l.bom_id} survey={survey} line={l} pointTypeId={null} />
            ))}
            <AddGeneralLine survey={survey} />
          </div>
        </div>
      )}
    </section>
  );
}
