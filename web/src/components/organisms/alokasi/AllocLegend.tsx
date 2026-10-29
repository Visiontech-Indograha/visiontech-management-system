import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { CELL_KINDS, CELL_LABEL, CELL_TONE } from "@/lib/alokasi";

/** Legenda warna sel matriks; setiap label juga tertulis di dalam sel (tidak hanya warna). */
export function AllocLegend() {
  return (
    <ListBlock aria-label="Keterangan warna sel" className="mb-3 flex flex-wrap gap-2 text-xs">
      {CELL_KINDS.map((kind) => (
        <ListEntry key={kind} className={`rounded-md border px-2 py-0.5 ${CELL_TONE[kind]}`}>
          {CELL_LABEL[kind]}
        </ListEntry>
      ))}
    </ListBlock>
  );
}
