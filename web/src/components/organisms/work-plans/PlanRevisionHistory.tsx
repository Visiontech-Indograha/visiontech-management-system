import { QueryState } from "@/components/molecules/QueryState";
import { formatDate, formatDateTime } from "@/lib/format";
import { usePlanRevisions, type PlanRevision } from "@/services/workPlanService";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { SectionTitle } from "@/components/molecules/SectionTitle";

type DiffItem = { field: string; label: string; before?: unknown; after?: unknown; added?: string[]; removed?: string[]; changed?: string[] };

const show = (v: unknown) => {
  if (v === null || v === undefined || v === "") return "-";
  if (typeof v === "boolean") return v ? "Ya" : "Tidak";
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)) return formatDate(v);
  return String(v);
};
const dates = (xs: string[]) => xs.map((x) => formatDate(x)).join(", ");

function DiffLine({ d }: { d: DiffItem }) {
  if (d.added || d.removed) {
    const isDays = d.field === "days";
    const fmt = (xs: string[]) => (isDays ? dates(xs) : xs.join(", "));
    return (
      <ListEntry>
        <TextBlock as="span" className="font-medium">{d.label}:</TextBlock>{" "}
        {d.added && d.added.length > 0 && <TextBlock as="span" className="text-success">+ {fmt(d.added)} </TextBlock>}
        {d.removed && d.removed.length > 0 && <TextBlock as="span" className="text-danger">− {fmt(d.removed)} </TextBlock>}
        {d.changed && d.changed.length > 0 && <TextBlock as="span" className="text-mist">diubah: {dates(d.changed)}</TextBlock>}
      </ListEntry>
    );
  }
  return (
    <ListEntry>
      <TextBlock as="span" className="font-medium">{d.label}:</TextBlock> {show(d.before)} → {show(d.after)}
    </ListEntry>
  );
}

/** Riwayat revisi rencana kerja: setiap baris menampilkan sebelum → sesudah, anggota +/−. */
export function PlanRevisionHistory({ planId }: { planId: string }) {
  const revisions = usePlanRevisions(planId);
  if (revisions.isSuccess && revisions.data.length === 0) return null;
  return (
    <section aria-label="Riwayat revisi" className="rounded-panel border border-line bg-surface p-4 shadow-card">
      <SectionTitle>Riwayat revisi</SectionTitle>
      <QueryState query={revisions} errorText="Riwayat revisi tidak dapat dimuat.">
        <ListBlock className="space-y-4">
          {revisions.data?.map((r: PlanRevision) => (
            <ListEntry key={r.id} className="text-sm">
              <TextBlock className="font-medium">
                Revisi ke-{Math.max(r.revision - 1, 1)} · {r.revised_by_name ?? "-"}
              </TextBlock>
              <TextBlock className="text-xs text-mist">{formatDateTime(r.created_at)}</TextBlock>
              <TextBlock className="mt-1">Alasan: {r.reason}</TextBlock>
              <ListBlock className="mt-1 list-disc space-y-0.5 pl-5">
                {(r.diff as DiffItem[]).map((d) => (
                  <DiffLine key={d.field} d={d} />
                ))}
              </ListBlock>
            </ListEntry>
          ))}
        </ListBlock>
      </QueryState>
    </section>
  );
}
