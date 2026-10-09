import { QueryState } from "@/components/molecules/QueryState";
import { formatDate, formatDateTime } from "@/lib/format";
import { usePlanRevisions, type PlanRevision } from "./api";

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
      <li>
        <span className="font-medium">{d.label}:</span>{" "}
        {d.added && d.added.length > 0 && <span className="text-success">+ {fmt(d.added)} </span>}
        {d.removed && d.removed.length > 0 && <span className="text-danger">− {fmt(d.removed)} </span>}
        {d.changed && d.changed.length > 0 && <span className="text-mist">diubah: {dates(d.changed)}</span>}
      </li>
    );
  }
  return (
    <li>
      <span className="font-medium">{d.label}:</span> {show(d.before)} → {show(d.after)}
    </li>
  );
}

/** Riwayat revisi rencana kerja: setiap baris menampilkan sebelum → sesudah, anggota +/−. */
export function RevisionHistory({ planId }: { planId: string }) {
  const revisions = usePlanRevisions(planId);
  if (revisions.isSuccess && revisions.data.length === 0) return null;
  return (
    <section aria-label="Riwayat revisi" className="rounded-panel border border-line bg-surface p-4 shadow-card">
      <h2 className="mb-3 text-base font-semibold">Riwayat revisi</h2>
      <QueryState query={revisions} errorText="Riwayat revisi tidak dapat dimuat.">
        <ul className="space-y-4">
          {revisions.data?.map((r: PlanRevision) => (
            <li key={r.id} className="text-sm">
              <p className="font-medium">
                Revisi ke-{Math.max(r.revision - 1, 1)} · {r.revised_by_name ?? "-"}
              </p>
              <p className="text-xs text-mist">{formatDateTime(r.created_at)}</p>
              <p className="mt-1">Alasan: {r.reason}</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                {(r.diff as DiffItem[]).map((d) => (
                  <DiffLine key={d.field} d={d} />
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}
