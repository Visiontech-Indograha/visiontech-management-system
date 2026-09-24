import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/VmsDialog";
import { TextField } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import { ApiError } from "@/lib/api";
import { ROLE_LABEL } from "@/lib/types";
import { useDeleteType, useDocumentTypes, useSaveType, type DocumentType } from "./api";

type Rule = DocumentType["rules"][number];
const EMPLOYMENT = { PERMANENT: "Tetap", CONTRACT: "Kontrak" } as const;

function describeRule(r: Rule): string {
  const who = r.user_type ? ROLE_LABEL[r.user_type] : r.role ? ROLE_LABEL[r.role] : "Semua role";
  return r.employment_type ? `${who} · ${EMPLOYMENT[r.employment_type as keyof typeof EMPLOYMENT]}` : who;
}

/** Kelola jenis berkas dan aturan wajib (FR-DOC-01). */
export function DocumentTypesPage() {
  const types = useDocumentTypes();
  const remove = useDeleteType();
  const [editing, setEditing] = useState<DocumentType | "new" | null>(null);
  const [deleting, setDeleting] = useState<DocumentType | null>(null);

  return (
    <>
      <PageHeader title="Jenis berkas" action={<Button onClick={() => setEditing("new")}>Tambah jenis</Button>} />
      <div className="overflow-x-auto rounded-panel border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Nama</th>
              <th className="px-4 py-3 font-medium">Kedaluwarsa</th>
              <th className="px-4 py-3 font-medium">Wajib bagi</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 text-right font-medium">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {types.data?.map((t) => (
              <tr key={t.id} className="border-b border-line last:border-0 hover:bg-hover">
                <td className="px-4 py-3 font-medium">{t.name}</td>
                <td className="px-4 py-3">{t.has_expiry ? "Ya" : "Tidak"}</td>
                <td className="px-4 py-3">
                  {t.rules.length === 0 ? <span className="text-mist">Opsional</span> : t.rules.map(describeRule).join("; ")}
                </td>
                <td className="px-4 py-3">{t.is_active ? <Badge tone="success">Aktif</Badge> : <Badge>Nonaktif</Badge>}</td>
                <td className="whitespace-nowrap px-4 py-3 text-right">
                  <Button variant="ghost" className="h-8 px-2" onClick={() => setEditing(t)}>
                    Ubah
                  </Button>
                  <Button variant="ghost" className="h-8 px-2 text-danger" onClick={() => setDeleting(t)}>
                    Hapus
                  </Button>
                </td>
              </tr>
            ))}
            {types.data?.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-mist">
                  Belum ada jenis berkas.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {editing && <TypeDialog key={editing === "new" ? "new" : editing.id} type={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
      <Dialog
        open={deleting !== null}
        title={deleting ? `Hapus ${deleting.name}?` : ""}
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
                  toast.success("Jenis berkas dihapus.");
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
        Berkas karyawan yang sudah ada tetap tersimpan sebagai riwayat, tetapi jenis ini tidak lagi dihitung wajib.
      </Dialog>
    </>
  );
}

const ROLE_OPTIONS = ["admin", "team_leader", "finance", "hes"] as const;

/** Satu baris aturan = satu pilihan kelompok + filter status kerja opsional. */
function TypeDialog({ type, onClose }: { type: DocumentType | null; onClose: () => void }) {
  const save = useSaveType();
  const [rules, setRules] = useState<Rule[]>(type?.rules ?? []);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const setRule = (i: number, patch: Partial<Rule>) => setRules(rules.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const group = (r: Rule) => (r.user_type ? `user:${r.user_type}` : r.role ? `role:${r.role}` : "all");
  const fromGroup = (v: string): Partial<Rule> => {
    if (v === "all") return { role: null, user_type: null };
    const [kind, val] = v.split(":");
    return kind === "user" ? { role: "user", user_type: val as "WTL" | "DRIVER" } : { role: val as Rule["role"], user_type: null };
  };

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = {
      name: String(f.get("name") ?? "").trim(),
      has_expiry: f.get("has_expiry") === "on",
      is_active: f.get("is_active") === "on",
      rules,
    };
    setErrors({});
    setFormError(null);
    try {
      await save.mutateAsync({ id: type?.id, body });
      toast.success("Jenis berkas disimpan.");
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Record<string, string>);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  return (
    <Dialog
      open
      title={type ? "Ubah jenis berkas" : "Tambah jenis berkas"}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Batal
          </Button>
          <Button type="submit" form="type-form" disabled={save.isPending}>
            Simpan
          </Button>
        </>
      }
    >
      <form id="type-form" onSubmit={submit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <TextField name="name" label="Nama" defaultValue={type?.name ?? ""} error={errors.name} />
        <label className="mb-2 flex items-center gap-2 text-sm">
          <input type="checkbox" name="has_expiry" defaultChecked={type?.has_expiry ?? false} /> Memiliki tanggal kedaluwarsa
        </label>
        <label className="mb-4 flex items-center gap-2 text-sm">
          <input type="checkbox" name="is_active" defaultChecked={type?.is_active ?? true} /> Aktif
        </label>

        <fieldset className="mb-2">
          <legend className="mb-1 text-sm font-medium">Wajib bagi</legend>
          <p className="mb-2 text-sm text-mist">Berkas wajib bila salah satu aturan cocok. Tanpa aturan = opsional.</p>
          {errors.rules && (
            <p role="alert" className="mb-2 text-sm text-danger">
              {errors.rules}
            </p>
          )}
          {rules.map((r, i) => (
            <div key={i} className="mb-2 flex gap-2">
              <select
                aria-label={`Kelompok aturan ${i + 1}`}
                className="h-10 flex-1 rounded-control border border-line bg-surface px-2 text-sm"
                value={group(r)}
                onChange={(e) => setRule(i, fromGroup(e.target.value))}
              >
                <option value="all">Semua role</option>
                <option value="user:WTL">WTL</option>
                <option value="user:DRIVER">Driver</option>
                {ROLE_OPTIONS.map((v) => (
                  <option key={v} value={`role:${v}`}>
                    {ROLE_LABEL[v]}
                  </option>
                ))}
              </select>
              <select
                aria-label={`Status kerja aturan ${i + 1}`}
                className="h-10 rounded-control border border-line bg-surface px-2 text-sm"
                value={r.employment_type ?? ""}
                onChange={(e) => setRule(i, { employment_type: (e.target.value || null) as Rule["employment_type"] })}
              >
                <option value="">Semua status</option>
                <option value="PERMANENT">Tetap</option>
                <option value="CONTRACT">Kontrak</option>
              </select>
              <Button variant="ghost" aria-label={`Hapus aturan ${i + 1}`} onClick={() => setRules(rules.filter((_, j) => j !== i))}>
                ×
              </Button>
            </div>
          ))}
          <Button variant="outline" onClick={() => setRules([...rules, { role: null, user_type: null, employment_type: null }])}>
            Tambah aturan
          </Button>
        </fieldset>
      </form>
    </Dialog>
  );
}
