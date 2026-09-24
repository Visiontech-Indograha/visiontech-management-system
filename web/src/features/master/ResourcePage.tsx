import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/VmsDialog";
import { SelectField, TextField } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import { api, ApiError } from "@/lib/api";
import { useDebouncedValue } from "@/lib/useDebouncedValue";

export interface FieldDef {
  name: string;
  label: string;
  type?: "text" | "number" | "select" | "checkbox";
  options?: { value: string; label: string }[];
  hint?: string;
  /** Hanya tampil saat membuat (mis. kategori yang tidak boleh diubah). */
  createOnly?: boolean;
  step?: string;
}

export interface ColumnDef<Row> {
  header: string;
  cell: (row: Row) => ReactNode;
  align?: "right";
}

interface Props<Row extends { id: string }> {
  title: string;
  /** Path API relatif terhadap /api/v1, mis. "/products". */
  endpoint: string;
  /** Parameter tetap pada daftar (mis. { category: "TOOL" }). */
  params?: Record<string, string>;
  /** Nilai tetap yang ikut dikirim saat membuat (mis. { category: "PROJECT_GOODS" }). */
  createDefaults?: Record<string, unknown>;
  columns: ColumnDef<Row>[];
  fields: FieldDef[];
  /** Permission (dari manage_permissions) yang diperlukan untuk tambah/ubah/hapus. */
  managePermission: string;
  noun: string; // mis. "produk"
  rowName: (row: Row) => string;
  toolbar?: ReactNode;
}

interface Page<Row> {
  items: Row[];
  total: number;
  page: number;
  page_size: number;
}

type Errors = Record<string, string>;

/** Tabel master + dialog form + hapus (soft delete). Dipakai semua halaman master data. */
export function ResourcePage<Row extends { id: string }>(props: Props<Row>) {
  const { title, endpoint, params, createDefaults, columns, fields, managePermission, noun, rowName } = props;
  const { me } = useSession();
  const canManage = !!me?.manage_permissions.includes(managePermission);
  const qc = useQueryClient();

  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const search = useDebouncedValue(q, 300);
  const key = ["master", endpoint, params, search, page];

  const list = useQuery({
    queryKey: key,
    queryFn: async () =>
      (await api.get<Page<Row>>(endpoint, { params: { ...params, q: search || undefined, page, page_size: 25 } })).data,
    placeholderData: keepPreviousData,
  });

  const [editing, setEditing] = useState<Row | "new" | null>(null);
  const [deleting, setDeleting] = useState<Row | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);

  const invalidate = () => qc.invalidateQueries({ queryKey: ["master", endpoint] });
  const save = useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      editing === "new" || editing === null
        ? (await api.post(endpoint, { ...createDefaults, ...body })).data
        : (await api.patch(`${endpoint}/${editing.id}`, body)).data,
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: async (row: Row) => api.delete(`${endpoint}/${row.id}`),
    onSuccess: invalidate,
  });

  const close = () => {
    setEditing(null);
    setErrors({});
    setFormError(null);
  };

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    for (const field of fields) {
      if (field.createOnly && editing !== "new") continue;
      if (field.type === "checkbox") {
        body[field.name] = f.get(field.name) === "on";
        continue;
      }
      const raw = String(f.get(field.name) ?? "").trim();
      body[field.name] = raw === "" ? (editing === "new" ? undefined : null) : raw;
    }
    setErrors({});
    setFormError(null);
    try {
      await save.mutateAsync(body);
      toast.success(editing === "new" ? `${cap(noun)} ditambahkan.` : "Perubahan disimpan.");
      close();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Errors);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  const data = list.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const current = editing && editing !== "new" ? editing : null;
  const colCount = columns.length + (canManage ? 1 : 0);

  return (
    <>
      <PageHeader
        title={title}
        action={canManage && <Button onClick={() => setEditing("new")}>{`Tambah ${noun}`}</Button>}
      />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          aria-label={`Cari ${noun}`}
          placeholder={`Cari ${noun}...`}
          className="h-10 w-64 rounded-control border border-line bg-surface px-3 text-sm"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
        {props.toolbar}
      </div>

      <div className="overflow-x-auto rounded-panel border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 border-b border-line bg-surface text-mist">
            <tr>
              {columns.map((c) => (
                <th key={c.header} className={`px-4 py-3 font-medium ${c.align === "right" ? "text-right" : ""}`}>
                  {c.header}
                </th>
              ))}
              {canManage && <th className="px-4 py-3 text-right font-medium">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {list.isPending && (
              <tr aria-hidden>
                <td colSpan={colCount} className="h-11 px-4">
                  <div className="h-3 w-1/2 animate-pulse rounded-tag bg-hover" />
                </td>
              </tr>
            )}
            {list.isError && (
              <tr>
                <td colSpan={colCount} className="px-4 py-6 text-center text-danger">
                  Data tidak dapat dimuat.{" "}
                  <button className="font-semibold underline" onClick={() => void list.refetch()}>
                    Coba lagi
                  </button>
                </td>
              </tr>
            )}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={colCount} className="px-4 py-6 text-center text-mist">
                  {search ? `Tidak ada ${noun} yang cocok.` : `Belum ada ${noun}.`}
                  {canManage && !search && (
                    <>
                      {" "}
                      <button className="font-semibold text-lens underline" onClick={() => setEditing("new")}>
                        {`Tambah ${noun}`}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            )}
            {data?.items.map((row) => (
              <tr key={row.id} className="h-11 border-b border-line last:border-0 hover:bg-hover">
                {columns.map((c) => (
                  <td key={c.header} className={`px-4 py-2 ${c.align === "right" ? "text-right" : ""}`}>
                    {c.cell(row)}
                  </td>
                ))}
                {canManage && (
                  <td className="whitespace-nowrap px-4 py-2 text-right">
                    <Button variant="ghost" className="h-8 px-2" onClick={() => setEditing(row)}>
                      Ubah
                    </Button>
                    <Button variant="ghost" className="h-8 px-2 text-danger" onClick={() => setDeleting(row)}>
                      Hapus
                    </Button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.total > data.page_size && (
        <nav aria-label="Halaman" className="mt-4 flex items-center justify-between text-sm">
          <span className="text-mist">
            {data.total} data · halaman {data.page} dari {lastPage}
          </span>
          <span className="flex gap-2">
            <Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Sebelumnya
            </Button>
            <Button variant="outline" disabled={page >= lastPage} onClick={() => setPage(page + 1)}>
              Berikutnya
            </Button>
          </span>
        </nav>
      )}

      <Dialog
        open={editing !== null}
        title={editing === "new" ? `Tambah ${noun}` : `Ubah ${noun}`}
        onClose={close}
        footer={
          <>
            <Button variant="outline" onClick={close}>
              Batal
            </Button>
            <Button type="submit" form="resource-form" disabled={save.isPending}>
              {save.isPending ? "Menyimpan..." : "Simpan"}
            </Button>
          </>
        }
      >
        <form id="resource-form" key={current?.id ?? "new"} onSubmit={submit} noValidate>
          {formError && (
            <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
              {formError}
            </p>
          )}
          {fields
            .filter((f) => !f.createOnly || editing === "new")
            .map((f) => {
              const value = current ? (current as unknown as Record<string, unknown>)[f.name] : undefined;
              if (f.type === "select")
                return (
                  <SelectField
                    key={f.name}
                    name={f.name}
                    label={f.label}
                    hint={f.hint}
                    error={errors[f.name]}
                    defaultValue={String(value ?? f.options?.[0]?.value ?? "")}
                  >
                    {f.options?.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </SelectField>
                );
              if (f.type === "checkbox")
                return (
                  <label key={f.name} className="mb-4 flex items-center gap-2 text-sm">
                    <input type="checkbox" name={f.name} defaultChecked={Boolean(value)} />
                    {f.label}
                  </label>
                );
              return (
                <TextField
                  key={f.name}
                  name={f.name}
                  label={f.label}
                  hint={f.hint}
                  type={f.type === "number" ? "number" : "text"}
                  step={f.step}
                  error={errors[f.name]}
                  defaultValue={value == null ? "" : String(value)}
                />
              );
            })}
        </form>
      </Dialog>

      <Dialog
        open={deleting !== null}
        title={deleting ? `Hapus ${rowName(deleting)}?` : ""}
        onClose={() => setDeleting(null)}
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleting(null)}>
              Batal
            </Button>
            <Button
              variant="destructive"
              disabled={remove.isPending}
              onClick={async () => {
                if (!deleting) return;
                try {
                  await remove.mutateAsync(deleting);
                  toast.success(`${cap(noun)} dihapus.`);
                } catch (e) {
                  toast.error(e instanceof ApiError ? e.message : "Terjadi kesalahan. Coba lagi.");
                }
                setDeleting(null);
              }}
            >
              Hapus
            </Button>
          </>
        }
      >
        Data tidak muncul lagi pada pilihan, tetapi tetap tampil pada riwayat yang sudah ada.
      </Dialog>
    </>
  );
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
