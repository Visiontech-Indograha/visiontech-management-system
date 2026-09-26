import { FilePreview } from "@/components/molecules/FilePreview";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/format";
import type { WorkPlan } from "./api";
import { useFinalReport, usePlanTeam } from "./report-api";

const ROLE: Record<string, string> = { LEADER: "Ketua", MEMBER: "Anggota" };

/** Tim SK di halaman detail: dulu hanya ketua yang tampil (temuan R-19). */
export function TeamCard({ plan }: { plan: WorkPlan }) {
  const team = usePlanTeam(plan.id);
  return (
    <section aria-label="Tim" className="mt-6 rounded-panel border border-line bg-surface shadow-card px-5 py-4">
      <h2 className="mb-2 text-base font-semibold">Tim</h2>
      {team.isPending && <Skeleton className="h-10 w-full" />}
      {team.isError && <p className="text-sm text-danger">Tim tidak dapat dimuat.</p>}
      {team.data?.length === 0 && <p className="text-sm text-mist">Belum ada anggota tim.</p>}
      {!!team.data?.length && (
        <ul className="divide-y divide-line text-sm">
          {team.data.map((m) => (
            <li key={m.employee_id} className="flex items-center justify-between gap-3 py-2">
              <span>
                <span className="font-medium">{m.full_name}</span>
                {m.position && <span className="text-mist"> · {m.position}</span>}
              </span>
              <span className="rounded-full bg-hover px-2.5 py-0.5 text-xs font-medium">{ROLE[m.role_in_plan] ?? m.role_in_plan}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Laporan akhir: PM membacanya sebelum menyetujui/mengembalikan penyelesaian (dulu tidak bisa dibaca
 * sama sekali — temuan R-19), tim melihat catatan pengembalian.
 */
export function FinalReportPanel({ plan }: { plan: WorkPlan }) {
  const report = useFinalReport(plan.id);
  const r = report.data;
  if (report.isPending || (!r && !report.isError)) return null;
  return (
    <section aria-label="Laporan akhir" className="mt-6 rounded-panel border border-line bg-surface shadow-card px-5 py-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold">Laporan akhir</h2>
        {r && <StatusBadge status={r.status} />}
      </div>
      {report.isError && <p className="text-sm text-danger">Laporan akhir tidak dapat dimuat.</p>}
      {r && (
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="text-mist">Laporan keseluruhan</dt>
            <dd className="whitespace-pre-line">{r.body}</dd>
          </div>
          <div>
            <dt className="text-mist">Kendala keseluruhan</dt>
            <dd className="whitespace-pre-line">{r.obstacle || "-"}</dd>
          </div>
          {r.evidence_file_ids.length > 0 && (
            <div>
              <dt className="text-mist">Lampiran ({r.evidence_file_ids.length})</dt>
              <dd className="mt-1 flex flex-wrap gap-2">
                {r.evidence_file_ids.map((id, i) => (
                  <FilePreview key={id} fileId={id} fileName={`Lampiran ${i + 1}`} />
                ))}
              </dd>
            </div>
          )}
          <div className="text-mist">
            Diajukan {r.submitted_by_name ?? "ketua tim"}
            {r.submitted_at && ` · ${formatDateTime(r.submitted_at)}`}
          </div>
          {r.review_note && (
            <div>
              <dt className="text-mist">
                Catatan {r.reviewed_by_name ?? "PM"}
                {r.reviewed_at && ` · ${formatDateTime(r.reviewed_at)}`}
              </dt>
              <dd>{r.review_note}</dd>
            </div>
          )}
        </dl>
      )}
    </section>
  );
}
