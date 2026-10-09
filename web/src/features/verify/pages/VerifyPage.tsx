import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/atoms/Button";
import { Skeleton } from "@/components/atoms/Skeleton";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { signerRoleLabel } from "@/lib/labels";

type VerifyOut = components["schemas"]["VerifyOut"];

const STATE: Record<string, { title: string; tone: string }> = {
  VALID: { title: "Tanda tangan sah", tone: "border-success-border bg-success-bg text-success" },
  REVOKED: { title: "Tanda tangan dicabut", tone: "border-danger-border bg-danger-bg text-danger" },
  DOCUMENT_CHANGED: { title: "Dokumen tidak cocok", tone: "border-danger-border bg-danger-bg text-danger" },
  KEY_EXPIRED: { title: "Kunci penandatanganan dicabut", tone: "border-warning-border bg-warning-bg text-warning" },
  UNKNOWN: { title: "Kode QR tidak dikenal", tone: "border-danger-border bg-danger-bg text-danger" },
};

const Row = ({ label, children }: { label: string; children: ReactNode }) => (
  <div className="flex flex-col gap-0.5 border-b border-line py-2 last:border-0 md:flex-row md:justify-between md:gap-4">
    <dt className="text-mist">{label}</dt>
    <dd className="break-all font-medium md:text-right">{children ?? "-"}</dd>
  </div>
);

/** PUBLIK (tanpa login): hasil pemindaian QR tanda tangan — GET /verify/{token}. */
export function VerifyPage() {
  const token = useParams()["*"] ?? "";
  const q = useQuery({
    queryKey: ["verify", token],
    queryFn: async () => (await api.get<VerifyOut>(`/verify/${token}`)).data,
    enabled: !!token,
    retry: false,
  });
  const v = q.data;
  const state = v ? (STATE[v.state] ?? STATE.UNKNOWN) : null;

  return (
    <main className="mx-auto w-full max-w-xl px-4 py-10">
      <h1 className="mb-1 text-2xl font-semibold">Verifikasi tanda tangan</h1>
      <p className="mb-6 text-mist">PT Visiontech — pemeriksaan keaslian dokumen ber-QR.</p>
      {!token && <p className="text-danger">Tautan verifikasi tidak lengkap.</p>}
      {token && q.isPending && <Skeleton className="h-40 w-full" />}
      {q.isError && (
        <div role="alert" className="rounded-panel border border-danger-border bg-danger-bg p-4 text-danger">
          <p className="mb-3">{errorMessage(q.error, "Verifikasi gagal. Coba lagi.")}</p>
          <Button variant="outline" size="sm" onClick={() => q.refetch()}>
            Coba lagi
          </Button>
        </div>
      )}
      {v && state && (
        <>
          <div role="status" className={`mb-4 rounded-panel border p-4 ${state.tone}`}>
            <p className="text-lg font-semibold">{state.title}</p>
            {v.note && <p className="text-sm">{v.note}</p>}
          </div>
          {v.state !== "UNKNOWN" && (
            <dl className="rounded-panel border border-line bg-surface shadow-card px-5 py-2 text-sm">
              <Row label="Nomor dokumen">{v.document_number}</Row>
              <Row label="Judul">{v.document_title}</Row>
              <Row label="Penanda tangan">{v.signer_name}</Row>
              <Row label="Jabatan">{[v.signer_position, v.signer_unit].filter(Boolean).join(" · ") || null}</Row>
              <Row label="Peran">{signerRoleLabel(v.signer_role)}</Row>
              <Row label="Waktu tanda tangan">{v.signed_at ? formatDateTime(v.signed_at) : null}</Row>
              <Row label="Nomor seri">{v.serial_number}</Row>
              <Row label="Algoritme / kunci">{[v.algorithm, v.key_id].filter(Boolean).join(" · ") || null}</Row>
              <Row label="SHA-256 dokumen">{v.document_sha256_hex}</Row>
            </dl>
          )}
        </>
      )}
    </main>
  );
}
