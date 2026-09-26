import { useState } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog } from "@/components/ui/VmsDialog";
import { SelectField, TextField } from "@/components/ui/Field";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import {
  useCreateDocument,
  useEmployeeDocuments,
  useUploadFile,
  useVerifyDocument,
  type EmployeeDocument,
} from "./api";
import { FilePreview } from "@/components/molecules/FilePreview";

type Errors = Record<string, string>;

/** Jenis baku — "SIM A"/"SIM C" dipakai aturan pengemudi kendaraan, jadi harus dipilih, bukan diketik. */
const DOC_TYPES = ["KTP", "SIM A", "SIM B I", "SIM B II", "SIM C", "MCU", "Sertifikat K3", "Kontrak kerja"];
const OTHER = "__other__";

/** Sisa hari sampai kedaluwarsa menurut tanggal WIB (M2: peringatan ≤ 30 hari). */
function daysUntil(isoDate: string): number {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
  return Math.round((Date.parse(isoDate) - Date.parse(today)) / 86_400_000);
}

function ExpiryWarning({ doc }: { doc: EmployeeDocument }) {
  if (!doc.expiry_date || doc.status !== "VERIFIED" || !["CURRENT", "EXPIRED"].includes(doc.lifecycle)) return null;
  const days = daysUntil(doc.expiry_date);
  if (days < 0 || doc.lifecycle === "EXPIRED") return <Badge tone="danger">Kedaluwarsa</Badge>;
  if (days <= 30) return <Badge tone="warning">{days === 0 ? "Berakhir hari ini" : `${days} hari lagi`}</Badge>;
  return null;
}

const STATUS: Record<string, { label: string; tone: "success" | "warning" | "danger" }> = {
  VERIFIED: { label: "Terverifikasi", tone: "success" },
  REJECTED: { label: "Ditolak", tone: "danger" },
};

/**
 * Daftar berkas karyawan + tambah (manage:employee_documents) + verifikasi (verify:documents) +
 * perpanjang per berkas (R8: tombolnya ada di daftar — termasuk "Berkas saya" — bukan hanya di detail).
 */
export function DocumentsPanel({
  employeeId,
  canManage,
  canVerify = false,
  canRenew = canManage,
}: {
  employeeId: string;
  canManage: boolean;
  canVerify?: boolean;
  canRenew?: boolean;
}) {
  const docs = useEmployeeDocuments(employeeId);
  const { me } = useSession();
  const [editing, setEditing] = useState(false);
  const [renewing, setRenewing] = useState<EmployeeDocument | null>(null);
  const showActions = canVerify || canRenew;
  const renewable = (d: EmployeeDocument) =>
    canRenew && d.status === "VERIFIED" && (d.lifecycle === "CURRENT" || d.lifecycle === "EXPIRED");

  return (
    <section aria-label="Berkas">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold">Berkas</h2>
        {canManage && <Button onClick={() => setEditing(true)}>Tambah berkas</Button>}
      </div>

      <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Berkas</th>
              <th className="px-4 py-3 font-medium">Nomor</th>
              <th className="px-4 py-3 font-medium">Kedaluwarsa</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">File</th>
              {showActions && <th className="px-4 py-3 text-right font-medium">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {docs.isPending && (
              <tr aria-hidden>
                <td colSpan={6} className="px-4 py-3">
                  <Skeleton className="h-4 w-1/2" />
                </td>
              </tr>
            )}
            {docs.isError && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-danger">
                  Berkas tidak dapat dimuat.{" "}
                  <Button variant="outline" size="sm" onClick={() => docs.refetch()}>
                    Coba lagi
                  </Button>
                </td>
              </tr>
            )}
            {docs.data?.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-mist">
                  Belum ada berkas.
                </td>
              </tr>
            )}
            {docs.data?.items.map((d) => (
              <tr key={d.id} className="h-11 border-b border-line last:border-0">
                <td className="px-4 py-2 font-medium">{d.doc_type}</td>
                <td className="px-4 py-2">{d.number_masked}</td>
                <td className="px-4 py-2">
                  {d.expiry_date ? (
                    <span className="flex flex-wrap items-center gap-2">
                      {formatDate(d.expiry_date)}
                      <ExpiryWarning doc={d} />
                    </span>
                  ) : (
                    "-"
                  )}
                </td>
                <td className="px-4 py-2">
                  <Badge tone={STATUS[d.status]?.tone ?? "warning"}>{STATUS[d.status]?.label ?? "Menunggu verifikasi"}</Badge>
                </td>
                <td className="px-4 py-2">
                  <FilePreview fileId={d.file_id} fileName={d.doc_type} />
                </td>
                {showActions && (
                  <td className="px-4 py-2 text-right">
                    {canVerify && d.status === "PENDING" && d.uploaded_by === me?.user_id && (
                      <span className="text-xs text-mist">Menunggu petugas lain</span>
                    )}
                    {canVerify && d.status === "PENDING" && d.uploaded_by !== me?.user_id && (
                      <VerifyActions employeeId={employeeId} doc={d} />
                    )}
                    {renewable(d) && (
                      <Button size="sm" variant="outline" aria-label={`Perpanjang ${d.doc_type}`} onClick={() => setRenewing(d)}>
                        Perpanjang
                      </Button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && <DocumentDialog employeeId={employeeId} onClose={() => setEditing(false)} />}
      {renewing && <DocumentDialog employeeId={employeeId} renew={renewing} onClose={() => setRenewing(null)} />}
    </section>
  );
}

function VerifyActions({ employeeId, doc }: { employeeId: string; doc: EmployeeDocument }) {
  const verify = useVerifyDocument(employeeId);
  const decide = (is_approved: boolean) =>
    verify.mutate(
      { docId: doc.id, is_approved },
      {
        onSuccess: () => toast.success(is_approved ? `${doc.doc_type} terverifikasi.` : `${doc.doc_type} ditolak.`),
        onError: (err) => toast.error(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi."),
      },
    );
  return (
    <span className="inline-flex gap-2">
      <Button size="sm" onClick={() => decide(true)} disabled={verify.isPending}>
        Verifikasi
      </Button>
      <Button size="sm" variant="outline" onClick={() => decide(false)} disabled={verify.isPending}>
        Tolak
      </Button>
    </span>
  );
}

function DocumentDialog({
  employeeId,
  renew,
  onClose,
}: {
  employeeId: string;
  /** Berkas yang diperpanjang: jenisnya tetap, berkas baru menggantikannya setelah diverifikasi. */
  renew?: EmployeeDocument;
  onClose: () => void;
}) {
  const upload = useUploadFile();
  const create = useCreateDocument(employeeId);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [other, setOther] = useState(false);
  const pending = upload.isPending || create.isPending;

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const picked = String(f.get("doc_type") ?? "");
    const doc_type = (picked === OTHER ? String(f.get("doc_type_other") ?? "") : picked).trim();
    const number = String(f.get("number") ?? "").trim();
    const expiry_date = String(f.get("expiry_date") ?? "").trim() || null;
    const fileInput = e.currentTarget.elements.namedItem("file") as HTMLInputElement;
    const file = fileInput.files?.[0];

    setErrors({});
    setFormError(null);

    if (!doc_type) return setErrors({ doc_type: "Wajib diisi." });
    if (!number) return setErrors({ number: "Wajib diisi." });
    if (!file || file.size === 0) return setErrors({ file: "File wajib dilampirkan." });

    try {
      const fileForm = new FormData();
      fileForm.set("file", file);
      const { file_id } = await upload.mutateAsync(fileForm);
      await create.mutateAsync({ doc_type, number, expiry_date, file_id, supersedes_id: renew?.id ?? null });
      toast.success(renew ? "Perpanjangan dikirim, menunggu verifikasi." : "Berkas ditambahkan.");
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Errors);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  return (
    <Dialog
      open
      title={renew ? "Perpanjang berkas" : "Tambah berkas"}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={pending}>
            Batal
          </Button>
          <Button type="submit" form="document-form" disabled={pending}>
            {pending ? "Menyimpan..." : "Simpan"}
          </Button>
        </>
      }
    >
      <form id="document-form" onSubmit={submit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        {renew ? (
          <p className="mb-4 text-sm">
            <input type="hidden" name="doc_type" value={renew.doc_type} />
            <span className="text-mist">Jenis dokumen: </span>
            <span className="font-medium">{renew.doc_type}</span>
            {renew.expiry_date && <span className="text-mist"> · berlaku sampai {formatDate(renew.expiry_date)}</span>}
          </p>
        ) : (
          <>
            <SelectField
              name="doc_type"
              label="Jenis dokumen"
              error={errors.doc_type}
              defaultValue=""
              onChange={(e) => setOther(e.target.value === OTHER)}
            >
              <option value="" disabled>
                Pilih jenis dokumen
              </option>
              {DOC_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
              <option value={OTHER}>Lainnya…</option>
            </SelectField>
            {other && <TextField name="doc_type_other" label="Jenis dokumen lainnya" hint="Contoh: SIO Excavator, Drone Pilot" />}
          </>
        )}
        <TextField name="number" label="Nomor dokumen" error={errors.number} />
        <TextField name="expiry_date" label="Tanggal kedaluwarsa" type="date" error={errors.expiry_date} hint="Bila ada." />
        <TextField name="file" label="File (jpg, png, pdf; maks. 10 MB)" type="file" accept=".jpg,.jpeg,.png,.pdf" error={errors.file} />
      </form>
    </Dialog>
  );
}
