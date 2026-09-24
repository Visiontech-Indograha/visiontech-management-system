import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/VmsDialog";
import { TextField } from "@/components/ui/Field";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import {
  useCreateDocument,
  useEmployeeDocuments,
  useUploadFile,
} from "./api";
import { FilePreview } from "@/components/molecules/FilePreview";

type Errors = Record<string, string>;

/** Daftar berkas + tambah (SA, HES) atau hanya lihat (pemilik). */
export function DocumentsPanel({ userId, canManage }: { userId: string; canManage: boolean }) {
  const docs = useEmployeeDocuments(userId);
  const [editing, setEditing] = useState(false);

  return (
    <section aria-label="Berkas">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold">Berkas</h2>
        {canManage && <Button onClick={() => setEditing(true)}>Tambah berkas</Button>}
      </div>

      <div className="overflow-x-auto rounded-panel border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Berkas</th>
              <th className="px-4 py-3 font-medium">Nomor</th>
              <th className="px-4 py-3 font-medium">Kedaluwarsa</th>
              <th className="px-4 py-3 font-medium">File</th>
              {canManage && <th className="px-4 py-3 text-right font-medium">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {docs.isError && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-danger">
                  Berkas tidak dapat dimuat.
                </td>
              </tr>
            )}
            {docs.data?.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-mist">
                  Belum ada berkas.
                </td>
              </tr>
            )}
            {docs.data?.items.map((d) => (
              <tr key={d.id} className="h-11 border-b border-line last:border-0">
                <td className="px-4 py-2 font-medium">{d.doc_type}</td>
                <td className="px-4 py-2">{d.number_masked ?? "-"}</td>
                <td className="px-4 py-2">
                  {d.expiry_date ? (
                    <span className="flex items-center gap-2">
                      {formatDate(d.expiry_date)}
                    </span>
                  ) : (
                    "-"
                  )}
                </td>
                <td className="px-4 py-2">
                  {d.file_id ? (<FilePreview fileId={d.file_id} fileName={d.doc_type ?? "Berkas"} />) : (
                    <span className="text-mist">Belum ada file</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && <DocumentDialog userId={userId} onClose={() => setEditing(false)} />}
    </section>
  );
}

function DocumentDialog({ userId, onClose }: { userId: string; onClose: () => void }) {
  const upload = useUploadFile();
  const create = useCreateDocument(userId);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const pending = upload.isPending || create.isPending;

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const doc_type = String(f.get("doc_type") ?? "").trim();
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
      const { id: file_id } = await upload.mutateAsync(fileForm);
      await create.mutateAsync({ doc_type, number, expiry_date, file_id });
      toast.success("Berkas ditambahkan.");
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Errors);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  return (
    <Dialog
      open
      title="Tambah berkas"
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
        <TextField name="doc_type" label="Jenis dokumen" error={errors.doc_type} hint="Contoh: KTP, SIM A, SIO Excavator" />
        <TextField name="number" label="Nomor dokumen" error={errors.number} />
        <TextField name="expiry_date" label="Tanggal kedaluwarsa" type="date" error={errors.expiry_date} hint="Bila ada." />
        <TextField name="file" label="File (jpg, png, pdf; maks. 10 MB)" type="file" accept=".jpg,.jpeg,.png,.pdf" error={errors.file} />
      </form>
    </Dialog>
  );
}
