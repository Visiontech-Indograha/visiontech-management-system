import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { signerRoleLabel } from "@/lib/labels";
import type { WorkPlan } from "@/services/workPlanService";
import { PlanPreviewDialog } from "./PlanPreviewDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";
import { FormBlock } from "@/components/molecules/FormBlock";
import { fetchDocumentPdf, listDocumentSignatures, listPlanDocuments, revokeSignature, type PlanDocument, type Signature } from "@/services/planDocumentService";


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
    const url = URL.createObjectURL(await fetchDocumentPdf(doc.id));
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
    queryFn: () => listPlanDocuments(plan.id),
  });
  return (
    <section aria-label="Dokumen" className="mt-6">
      <TextBlock as="h2" className="mb-3 text-base font-semibold">Dokumen</TextBlock>
      <QueryState query={docs} errorText="Dokumen tidak dapat dimuat." empty={docs.data?.length === 0} emptyText="Belum ada dokumen rencana kerja.">
        <ListBlock className="space-y-4">
          {docs.data?.map((d) => (
            <DocumentCard key={d.id} doc={d} />
          ))}
        </ListBlock>
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
    queryFn: () => listDocumentSignatures(doc.id),
  });

  return (
    <ListEntry className="rounded-panel border border-line bg-surface shadow-card p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <TextBlock className="font-semibold">
            {doc.number} · versi {doc.version}
          </TextBlock>
          <TextBlock className="text-sm text-mist">
            {KIND_LABEL[doc.kind] ?? doc.kind} · terbit {formatDateTime(doc.issued_at)}
            {doc.accepted_at && ` · diterima ${formatDateTime(doc.accepted_at)}`}
          </TextBlock>
          {doc.reason && <TextBlock className="text-sm text-mist">Alasan: {doc.reason}</TextBlock>}
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={doc.status} />
          <ActionButton variant="outline" size="sm" onClick={() => setViewing(true)}>
            Lihat dokumen
          </ActionButton>
          <ActionButton
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
          </ActionButton>
        </div>
      </div>
      {viewing && (
        <PlanPreviewDialog title={`${doc.number} · versi ${doc.version}`} path={`/documents/${doc.id}/html`} onClose={() => setViewing(false)} />
      )}
      <TextBlock className="mb-2 break-all text-xs text-mist">SHA-256: {doc.sha256}</TextBlock>
      <QueryState query={sigs} errorText="Tanda tangan tidak dapat dimuat." empty={sigs.data?.length === 0} emptyText="Belum ada tanda tangan.">
        <div className="overflow-x-auto">
          <TableBlock className="w-full text-left text-sm">
            <TableBlockHead className="border-b border-line text-mist">
              <TableBlockRow>
                <TableBlockHeaderCell className="py-2 pr-3 font-medium">Penanda tangan</TableBlockHeaderCell>
                <TableBlockHeaderCell className="py-2 pr-3 font-medium">Peran</TableBlockHeaderCell>
                <TableBlockHeaderCell className="py-2 pr-3 font-medium">Waktu</TableBlockHeaderCell>
                <TableBlockHeaderCell className="py-2 pr-3 font-medium">Status</TableBlockHeaderCell>
                {canRevoke && <TableBlockHeaderCell className="py-2 text-right font-medium">Aksi</TableBlockHeaderCell>}
              </TableBlockRow>
            </TableBlockHead>
            <TableBlockBody>
              {sigs.data?.map((s) => (
                <TableBlockRow key={s.id} className="border-b border-line last:border-0">
                  <TableBlockCell className="py-2 pr-3">
                    <TextBlock as="span" className="font-medium">{s.signer_name}</TextBlock>
                    <TextBlock as="span" className="block text-xs text-mist">{s.signer_position}</TextBlock>
                  </TableBlockCell>
                  <TableBlockCell className="py-2 pr-3">{signerRoleLabel(s.signer_role)}</TableBlockCell>
                  <TableBlockCell className="py-2 pr-3">{formatDateTime(s.signed_at)}</TableBlockCell>
                  <TableBlockCell className="py-2 pr-3">
                    {s.revoked_at ? (
                      <TextBlock as="span" className="text-danger" title={s.revoked_reason ?? undefined}>
                        Dicabut {formatDateTime(s.revoked_at)}
                      </TextBlock>
                    ) : (
                      "Berlaku"
                    )}
                  </TableBlockCell>
                  {canRevoke && (
                    <TableBlockCell className="py-2 text-right">
                      {!s.revoked_at && (
                        <ActionButton variant="outline" size="sm" onClick={() => setRevoking(s)}>
                          Cabut tanda tangan
                        </ActionButton>
                      )}
                    </TableBlockCell>
                  )}
                </TableBlockRow>
              ))}
            </TableBlockBody>
          </TableBlock>
        </div>
      </QueryState>
      {revoking && <RevokeDialog documentId={doc.id} signature={revoking} onClose={() => setRevoking(null)} />}
    </ListEntry>
  );
}

function RevokeDialog({ documentId, signature, onClose }: { documentId: string; signature: Signature; onClose: () => void }) {
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const revoke = useMutation({
    mutationFn: (body: components["schemas"]["RevokeRequest"]) => revokeSignature(signature.id, body),
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
          <ActionButton variant="outline" onClick={onClose} disabled={revoke.isPending}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="revoke-form" variant="destructive" disabled={revoke.isPending}>
            {revoke.isPending ? "Mencabut..." : "Cabut"}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="revoke-form" onSubmit={submit} noValidate>
        {formError && (
          <TextBlock role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </TextBlock>
        )}
        <TextBlock className="mb-3 text-sm">
          Tanda tangan {signature.signer_name} ({signerRoleLabel(signature.signer_role)}) akan dicabut. Pencabutan tercatat di audit dan
          tidak dapat dibatalkan.
        </TextBlock>
        <TextAreaField label="Alasan pencabutan" value={reason} onChange={(e) => setReason(e.target.value)} error={error ?? undefined} />
      </FormBlock>
    </VmsDialog>
  );
}
