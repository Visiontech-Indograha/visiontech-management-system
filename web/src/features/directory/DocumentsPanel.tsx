import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/VmsDialog";
import { SelectField, TextField } from "@/components/ui/Field";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import {
  useCreateDocument,
  useDeleteDocument,
  useDocumentTypes,
  useEmployeeDocuments,
  useUpdateDocument,
  type EmployeeDocument,
} from "./api";
import { ExpiryBadge } from "./badges";

type Errors = Record<string, string>;

/** Daftar berkas + tambah/ubah/hapus (SA, HES) atau hanya lihat (pemilik). */
export function DocumentsPanel({ userId, canManage }: { userId: string; canManage: boolean }) {
  const docs = useEmployeeDocuments(userId);
  const [editing, setEditing] = useState<EmployeeDocument | "new" | null>(null);
  const [deleting, setDeleting] = useState<EmployeeDocument | null>(null);
  const remove = useDeleteDocument(userId);

  return (
    <section aria-label="Berkas">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold">Berkas</h2>
        {canManage && <Button onClick={() => setEditing("new")}>Tambah berkas</Button>}
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
            {docs.data?.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-mist">
                  Belum ada berkas.
                </td>
              </tr>
            )}
            {docs.data?.map((d) => (
              <tr key={d.id} className="h-11 border-b border-line last:border-0">
                <td className="px-4 py-2 font-medium">{d.type_name ?? d.custom_label}</td>
                <td className="px-4 py-2">{d.document_number ?? "-"}</td>
                <td className="px-4 py-2">
                  {d.expires_at ? (
                    <span className="flex items-center gap-2">
                      {formatDate(d.expires_at)}
                      <ExpiryBadge level={d.expiry_level} days={d.days_left} />
                    </span>
                  ) : (
                    "-"
                  )}
                </td>
                <td className="px-4 py-2">
                  {d.file_url ? (
                    <a href={`${import.meta.env.VITE_API_BASE_URL ?? ""}${d.file_url}`} className="text-lens hover:underline" target="_blank" rel="noreferrer">
                      Buka
                    </a>
                  ) : (
                    <span className="text-mist">Belum ada file</span>
                  )}
                </td>
                {canManage && (
                  <td className="whitespace-nowrap px-4 py-2 text-right">
                    <Button variant="ghost" className="h-8 px-2" onClick={() => setEditing(d)}>
                      Ubah
                    </Button>
                    <Button variant="ghost" className="h-8 px-2 text-danger" onClick={() => setDeleting(d)}>
                      Hapus
                    </Button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <DocumentDialog key={editing === "new" ? "new" : editing.id} userId={userId} doc={editing === "new" ? null : editing} onClose={() => setEditing(null)} />
      )}
      <Dialog
        open={deleting !== null}
        title={deleting ? `Hapus ${deleting.type_name ?? deleting.custom_label}?` : ""}
        onClose={() => setDeleting(null)}
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleting(null)}>
              Batal
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (!deleting) return;
                try {
                  await remove.mutateAsync(deleting.id);
                  toast.success("Berkas dihapus.");
                } catch (e) {
                  toast.error(e instanceof ApiError ? e.message : "Terjadi kesalahan.");
                }
                setDeleting(null);
              }}
            >
              Hapus
            </Button>
          </>
        }
      >
        Baris berkas dihapus dari daftar dan perubahan dicatat pada audit log.
      </Dialog>
    </section>
  );
}

function DocumentDialog({ userId, doc, onClose }: { userId: string; doc: EmployeeDocument | null; onClose: () => void }) {
  const types = useDocumentTypes();
  const create = useCreateDocument(userId);
  const update = useUpdateDocument(userId);
  const [mode, setMode] = useState<"type" | "label">(doc?.document_type_id || !doc ? "type" : "label");
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const editing = doc !== null;
  const pending = create.isPending || update.isPending;

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const form = new FormData();
    const clear: string[] = [];
    const put = (name: string, remove = false) => {
      const v = String(f.get(name) ?? "").trim();
      if (v) form.set(name, v);
      else if (editing && remove && doc[name as keyof EmployeeDocument] != null) clear.push(name);
    };
    if (!editing) {
      if (mode === "type") put("document_type_id");
      else put("custom_label");
    } else if (!doc.document_type_id) put("custom_label");
    put("document_number", true);
    put("issued_at", true);
    put("expires_at", true);
    put("notes", true);
    clear.forEach((c) => form.append("clear", c));
    const file = (f.get("file") as File | null) ?? null;
    if (file && file.size > 0) form.set("file", file);

    setErrors({});
    setFormError(null);
    try {
      if (editing) await update.mutateAsync({ id: doc.id, form });
      else await create.mutateAsync(form);
      toast.success(editing ? "Perubahan disimpan." : "Berkas ditambahkan.");
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Errors);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  const canAttach = !editing || !doc.file_id;

  return (
    <Dialog
      open
      title={editing ? "Ubah berkas" : "Tambah berkas"}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
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
        {!editing && (
          <div role="group" aria-label="Sumber jenis" className="mb-4 flex rounded-control border border-line p-0.5 text-sm">
            {(["type", "label"] as const).map((m) => (
              <button
                key={m}
                type="button"
                aria-pressed={mode === m}
                onClick={() => setMode(m)}
                className={`h-9 flex-1 rounded-control font-medium ${mode === m ? "bg-lens-soft text-lens" : "text-mist"}`}
              >
                {m === "type" ? "Jenis berkas" : "Label bebas"}
              </button>
            ))}
          </div>
        )}
        {!editing && mode === "type" && (
          <SelectField name="document_type_id" label="Jenis berkas" error={errors.document_type_id} defaultValue="">
            <option value="" disabled>
              Pilih jenis...
            </option>
            {types.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
                {t.has_expiry ? " (ada kedaluwarsa)" : ""}
              </option>
            ))}
          </SelectField>
        )}
        {((!editing && mode === "label") || (editing && !doc.document_type_id)) && (
          <TextField name="custom_label" label="Label" defaultValue={doc?.custom_label ?? ""} error={errors.custom_label} />
        )}
        <TextField name="document_number" label="Nomor" defaultValue={doc?.document_number ?? ""} error={errors.document_number} />
        <TextField name="issued_at" label="Tanggal terbit" type="date" defaultValue={doc?.issued_at ?? ""} error={errors.issued_at} />
        <TextField
          name="expires_at"
          label="Tanggal kedaluwarsa"
          type="date"
          defaultValue={doc?.expires_at ?? ""}
          error={errors.expires_at}
          hint="Wajib untuk jenis berkas yang memiliki kedaluwarsa."
        />
        <TextField name="notes" label="Catatan" defaultValue={doc?.notes ?? ""} error={errors.notes} />
        {canAttach ? (
          <TextField name="file" label="File (jpg, png, pdf; maks. 10 MB)" type="file" accept=".jpg,.jpeg,.png,.pdf" error={errors.file} />
        ) : (
          <p className="text-sm text-mist">Untuk mengganti file, tambahkan baris berkas baru agar riwayat tetap ada.</p>
        )}
      </form>
    </Dialog>
  );
}
