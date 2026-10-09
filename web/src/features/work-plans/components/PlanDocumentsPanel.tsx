import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/atoms/Button";
import { TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { api, ApiError } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { signerRoleLabel } from "@/lib/labels";
import type { WorkPlan } from "../workPlanService";
import { PlanPreviewDialog } from "./PlanPreviewDialog";

type PlanDocument = components["schemas"]["PlanDocumentOut"];
type Signature = components["schemas"]["SignatureOut"];

const PDF_UNAVAILABLE = "Pembuatan PDF sedang tidak tersedia. Coba lagi nanti atau hubungi admin.";
const KIND_LABEL: Record<string, string> = {
  INITIAL_ORDER: "Rencana Kerja",
  REVISION: "Revisi",
  ADDENDUM: "Revisi",
  PERSONNEL_ADDENDUM: "Revisi personel",
};

/** Unduh PDF bertanda tangan (GET /documents/{id}/pdf, blob). */
async function downloadPdf(doc: PlanDocument) {
  try {
    const res = await api.get<Blob>(`/documents/${doc.id}/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.number}-v${doc.version}.pdf`.replace(/\//g, "-");
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    // Badan galat berbentuk Blob sehingga pesan API tidak terbaca; 503 = layanan PDF tidak terpasang.
    toast.error(err instanceof ApiError && err.status === 503 ? PDF_UNAVAILABLE : errorMessage(err));
  }
}

/** Bagian "Dokumen": versi SK/revisi/adendum beserta tanda tangan ber-QR (Fase 6). */
export function PlanDocumentsPanel({ plan }: { plan: WorkPlan }) {
  const docs = useQuery({
    queryKey: ["plan-documents", plan.id],
    queryFn: async () => (await api.get<PlanDocument[]>(`/work-plans/${plan.id}/documents`)).data,
  });
  return (
    <section aria-label="Dokumen" className="mt-6">
      <h2 className="mb-3 text-base font-semibold">Dokumen</h2>
      <QueryState query={docs} errorText="Dokumen tidak dapat dimuat." empty={docs.data?.length === 0} emptyText="Belum ada dokumen rencana kerja.">
        <ul className="space-y-4">
          {docs.data?.map((d) => (
            <DocumentCard key={d.id} doc={d} />
          ))}
        </ul>
      </QueryState>
    </section>
  );
}

function DocumentCard({ doc }: { doc: PlanDocument }) {
  const { me } = useSession();
  // Pencabutan hanya untuk PM unit/OPS SK tersebut — API yang menegakkan; tombol untuk pemegang create:plan.
  const canRevoke = !!me?.permissions.includes("create:plan");
  const [busy, setBusy] = useState(false);
  const [revoking, setRevoking] = useState<Signature | null>(null);
  const [viewing, setViewing] = useState(false);
  const sigs = useQuery({
    queryKey: ["document-signatures", doc.id],
    queryFn: async () => (await api.get<Signature[]>(`/documents/${doc.id}/signatures`)).data,
  });

  return (
    <li className="rounded-panel border border-line bg-surface shadow-card p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold">
            {doc.number} · versi {doc.version}
          </p>
          <p className="text-sm text-mist">
            {KIND_LABEL[doc.kind] ?? doc.kind} · terbit {formatDateTime(doc.issued_at)}
            {doc.accepted_at && ` · diterima ${formatDateTime(doc.accepted_at)}`}
          </p>
          {doc.reason && <p className="text-sm text-mist">Alasan: {doc.reason}</p>}
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={doc.status} />
          <Button variant="outline" size="sm" onClick={() => setViewing(true)}>
            Lihat dokumen
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              await downloadPdf(doc);
              setBusy(false);
            }}
          >
            {busy ? "Mengunduh..." : "Unduh PDF"}
          </Button>
        </div>
      </div>
      {viewing && (
        <PlanPreviewDialog title={`${doc.number} · versi ${doc.version}`} path={`/documents/${doc.id}/html`} onClose={() => setViewing(false)} />
      )}
      <p className="mb-2 break-all text-xs text-mist">SHA-256: {doc.sha256}</p>
      <QueryState query={sigs} errorText="Tanda tangan tidak dapat dimuat." empty={sigs.data?.length === 0} emptyText="Belum ada tanda tangan.">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-mist">
              <tr>
                <th className="py-2 pr-3 font-medium">Penanda tangan</th>
                <th className="py-2 pr-3 font-medium">Peran</th>
                <th className="py-2 pr-3 font-medium">Waktu</th>
                <th className="py-2 pr-3 font-medium">Status</th>
                {canRevoke && <th className="py-2 text-right font-medium">Aksi</th>}
              </tr>
            </thead>
            <tbody>
              {sigs.data?.map((s) => (
                <tr key={s.id} className="border-b border-line last:border-0">
                  <td className="py-2 pr-3">
                    <span className="font-medium">{s.signer_name}</span>
                    <span className="block text-xs text-mist">{s.signer_position}</span>
                  </td>
                  <td className="py-2 pr-3">{signerRoleLabel(s.signer_role)}</td>
                  <td className="py-2 pr-3">{formatDateTime(s.signed_at)}</td>
                  <td className="py-2 pr-3">
                    {s.revoked_at ? (
                      <span className="text-danger" title={s.revoked_reason ?? undefined}>
                        Dicabut {formatDateTime(s.revoked_at)}
                      </span>
                    ) : (
                      "Berlaku"
                    )}
                  </td>
                  {canRevoke && (
                    <td className="py-2 text-right">
                      {!s.revoked_at && (
                        <Button variant="outline" size="sm" onClick={() => setRevoking(s)}>
                          Cabut tanda tangan
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </QueryState>
      {revoking && <RevokeDialog documentId={doc.id} signature={revoking} onClose={() => setRevoking(null)} />}
    </li>
  );
}

function RevokeDialog({ documentId, signature, onClose }: { documentId: string; signature: Signature; onClose: () => void }) {
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const revoke = useMutation({
    mutationFn: async (body: components["schemas"]["RevokeRequest"]) =>
      (await api.post<{ message: string }>(`/signatures/${signature.id}/revoke`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document-signatures", documentId] }),
  });
  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setFormError(null);
    if (!reason.trim()) return setError("Alasan pencabutan wajib diisi.");
    try {
      const out = await revoke.mutateAsync({ reason: reason.trim() });
      toast.success(out.message || "Tanda tangan dicabut.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };
  return (
    <VmsDialog
      open
      title="Cabut tanda tangan"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={revoke.isPending}>
            Batal
          </Button>
          <Button type="submit" form="revoke-form" variant="destructive" disabled={revoke.isPending}>
            {revoke.isPending ? "Mencabut..." : "Cabut"}
          </Button>
        </>
      }
    >
      <form id="revoke-form" onSubmit={submit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <p className="mb-3 text-sm">
          Tanda tangan {signature.signer_name} ({signerRoleLabel(signature.signer_role)}) akan dicabut. Pencabutan tercatat di audit dan
          tidak dapat dibatalkan.
        </p>
        <TextAreaField label="Alasan pencabutan" value={reason} onChange={(e) => setReason(e.target.value)} error={error ?? undefined} />
      </form>
    </VmsDialog>
  );
}
