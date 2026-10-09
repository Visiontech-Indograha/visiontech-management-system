import { useState } from "react";
import { toast } from "sonner";
import { FilePreview } from "@/components/molecules/FilePreview";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { api, ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import type { WorkPlan } from "@/services/workPlanService";
import { PlanPreviewDialog } from "./PlanPreviewDialog";
import { useFinalReport, usePlanTeam } from "@/services/reportService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

const ROLE: Record<string, string> = { LEADER: "Ketua", MEMBER: "Anggota" };

/** Tim SK di halaman detail: dulu hanya ketua yang tampil (temuan R-19). */
export function TeamCard({ plan }: { plan: WorkPlan }) {
  const team = usePlanTeam(plan.id);
  return (
    <section aria-label="Tim" className="mt-6 rounded-panel border border-line bg-surface shadow-card px-5 py-4">
      <TextBlock as="h2" className="mb-2 text-base font-semibold">Tim</TextBlock>
      {team.isPending && <LoadingBar className="h-10 w-full" />}
      {team.isError && <TextBlock className="text-sm text-danger">Tim tidak dapat dimuat.</TextBlock>}
      {team.data?.length === 0 && <TextBlock className="text-sm text-mist">Belum ada anggota tim.</TextBlock>}
      {!!team.data?.length && (
        <ListBlock className="divide-y divide-line text-sm">
          {team.data.map((m) => (
            <ListEntry key={m.employee_id} className="flex items-center justify-between gap-3 py-2">
              <TextBlock as="span">
                <TextBlock as="span" className="font-medium">{m.full_name}</TextBlock>
                {m.position && <TextBlock as="span" className="text-mist"> · {m.position}</TextBlock>}
              </TextBlock>
              <TextBlock as="span" className="rounded-full bg-hover px-2.5 py-0.5 text-xs font-medium">{ROLE[m.role_in_plan] ?? m.role_in_plan}</TextBlock>
            </ListEntry>
          ))}
        </ListBlock>
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
        <TextBlock as="h2" className="text-base font-semibold">Laporan akhir</TextBlock>
        {r && <StatusBadge status={r.status} />}
      </div>
      {r?.status === "APPROVED" && <FinalReportView plan={plan} />}
      {r?.status === "APPROVED" && (
        <ActionButton
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
        </ActionButton>
      )}
      {report.isError && <TextBlock className="text-sm text-danger">Laporan akhir tidak dapat dimuat.</TextBlock>}
      {r && (
        <ListBlock as="dl" className="space-y-3 text-sm">
          <div>
            <TextBlock as="dt" className="text-mist">Laporan keseluruhan</TextBlock>
            <TextBlock as="dd" className="whitespace-pre-line">{r.body}</TextBlock>
          </div>
          <div>
            <TextBlock as="dt" className="text-mist">Kendala keseluruhan</TextBlock>
            <TextBlock as="dd" className="whitespace-pre-line">{r.obstacle || "-"}</TextBlock>
          </div>
          {r.evidence_file_ids.length > 0 && (
            <div>
              <TextBlock as="dt" className="text-mist">Lampiran ({r.evidence_file_ids.length})</TextBlock>
              <TextBlock as="dd" className="mt-1 flex flex-wrap gap-2">
                {r.evidence_file_ids.map((id, i) => (
                  <FilePreview key={id} fileId={id} fileName={`Lampiran ${i + 1}`} />
                ))}
              </TextBlock>
            </div>
          )}
          <TextBlock as="span" className="block text-mist">
            Diajukan {r.submitted_by_name ?? "ketua tim"}
            {r.submitted_at && ` · ${formatDateTime(r.submitted_at)}`}
          </TextBlock>
          {r.review_note && (
            <div>
              <TextBlock as="dt" className="text-mist">
                Catatan {r.reviewed_by_name ?? "PM"}
                {r.reviewed_at && ` · ${formatDateTime(r.reviewed_at)}`}
              </TextBlock>
              <TextBlock as="dd">{r.review_note}</TextBlock>
            </div>
          )}
        </ListBlock>
      )}
    </section>
  );
}

/** Laporan akhir yang disetujui sebagai dokumen A4 (TTD ketua & PM + QR). */
function FinalReportView({ plan }: { plan: WorkPlan }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <ActionButton variant="outline" className="mr-2" onClick={() => setOpen(true)}>
        Lihat laporan akhir
      </ActionButton>
      {open && (
        <PlanPreviewDialog title={`Laporan akhir — ${plan.title}`} path={`/work-plans/${plan.id}/completion/html`} onClose={() => setOpen(false)} />
      )}
    </>
  );
}
