import { Pill } from "@/components/molecules/Pill";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDateTime } from "@/lib/format";
import type { CompletionVerification } from "@/services/exportService";

/** Judul halaman verifikasi. */
export function VerifyHeading() {
  return <TextBlock as="h1" className="text-center text-xl font-semibold">Verifikasi Dokumen VMS</TextBlock>;
}

/** Hasil pemeriksaan keaslian BAST resmi dari QR: hanya data yang memang tercetak di dokumen. */
export function CompletionVerificationCard({ data, pending, failed }: {
  data: CompletionVerification | undefined;
  pending: boolean;
  failed: boolean;
}) {
  if (pending) {
    return (
      <section className="space-y-2 rounded-panel border border-line bg-surface p-5 shadow-card">
        <LoadingBar className="h-6 w-48" />
        <LoadingBar className="h-24 w-full" />
      </section>
    );
  }
  if (failed || !data) {
    return (
      <section role="alert" className="rounded-panel border border-line bg-surface p-5 shadow-card">
        <Pill tone="danger">Tidak terverifikasi</Pill>
        <TextBlock className="mt-3 text-sm">
          Dokumen tidak dikenali. Kode verifikasi salah, terpotong, atau dokumen belum disahkan PM.
        </TextBlock>
      </section>
    );
  }
  const rows: [string, string][] = [
    ["Nomor", data.order_number ?? "-"],
    ["Klien", data.client_name ?? "-"],
    ["Pekerjaan", data.project_title ?? "-"],
    ["Ketua tim", `${data.leader_signer_name ?? "-"} · ${formatDateTime(data.leader_signed_at)}`],
    ["Project Manager", `${data.pm_signer_name ?? "-"} · ${formatDateTime(data.pm_signed_at)}`],
  ];
  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface p-5 shadow-card" data-testid="verify-result">
      {data.intact ? <Pill tone="success">Asli & tidak berubah</Pill> : <Pill tone="danger">Isi berubah sejak disahkan</Pill>}
      <TextBlock className="text-sm text-mist">
        {data.intact
          ? "Berita acara ini diterbitkan sistem VMS Visiontech dan isinya sama dengan saat disahkan."
          : "Data order di sistem sudah berbeda dari dokumen yang disahkan. Jangan gunakan dokumen ini sebagai acuan."}
      </TextBlock>
      <div className="grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <TextBlock as="span" className="text-mist">{k}</TextBlock>
            <TextBlock as="span">{v}</TextBlock>
          </div>
        ))}
      </div>
      <TextBlock className="break-all font-mono text-2xs text-mist">{`SHA-256: ${data.signature_hash}`}</TextBlock>
    </section>
  );
}
