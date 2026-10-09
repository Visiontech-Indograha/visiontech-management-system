import { useState } from "react";
import { toast } from "sonner";
import { FilePreview } from "@/components/molecules/FilePreview";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/atoms/Button";
import { Skeleton } from "@/components/atoms/Skeleton";
import { api, ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import type { WorkPlan } from "@/services/workPlanService";
import { PlanPreviewDialog } from "./PlanPreviewDialog";
import { useFinalReport, usePlanTeam } from "@/services/reportService";

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

/** PDF laporan akhir ber-QR (GET /work-plans/{id}/completion/pdf, blob) — tersedia setelah disetujui. */
async function downloadFinalReportPdf(plan: WorkPlan) {
  try {
    const res = await api.get<Blob>(`/work-plans/${plan.id}/completion/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${plan.number ?? "RK"}-laporan-akhir.pdf`.replace(/\//g, "-");
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    // Badan galat berbentuk Blob; 503 = layanan PDF tidak terpasang di server ini.
    toast.error(err instanceof ApiError && err.status === 503 ? "Pembuatan PDF sedang tidak tersedia. Coba lagi nanti atau hubungi admin." : errorMessage(err));
  }
}

/**
 * Laporan akhir: PM membacanya sebelum menyetujui/mengembalikan penyelesaian (dulu tidak bisa dibaca
 * sama sekali — temuan R-19), tim melihat catatan pengembalian.
 */
export function FinalReportPanel({ plan }: { plan: WorkPlan }) {
  const report = useFinalReport(plan.id);
  const [downloading, setDownloading] = useState(false);
  const r = report.data;
  if (report.isPending || (!r && !report.isError)) return null;
  return (
    <section aria-label="Laporan akhir" className="mt-6 rounded-panel border border-line bg-surface shadow-card px-5 py-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold">Laporan akhir</h2>
        {r && <StatusBadge status={r.status} />}
      </div>
      {r?.status === "APPROVED" && <FinalReportView plan={plan} />}
      {r?.status === "APPROVED" && (
        <Button
          variant="outline"
          className="mb-3"
          disabled={downloading}
          onClick={async () => {
            setDownloading(true);
            await downloadFinalReportPdf(plan);
            setDownloading(false);
          }}
        >
          {downloading ? "Mengunduh..." : "Unduh PDF laporan akhir"}
        </Button>
      )}
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

/** Laporan akhir yang disetujui sebagai dokumen A4 (TTD ketua & PM + QR). */
function FinalReportView({ plan }: { plan: WorkPlan }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="outline" className="mr-2" onClick={() => setOpen(true)}>
        Lihat laporan akhir
      </Button>
      {open && (
        <PlanPreviewDialog title={`Laporan akhir — ${plan.title}`} path={`/work-plans/${plan.id}/completion/html`} onClose={() => setOpen(false)} />
      )}
    </>
  );
}
