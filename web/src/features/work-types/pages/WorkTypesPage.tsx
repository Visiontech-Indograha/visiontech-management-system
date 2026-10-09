import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/atoms/Button";
import { TextField } from "@/components/molecules/Field";
import { PageHeader } from "@/components/organisms/PageHeader";
import { Skeleton } from "@/components/atoms/Skeleton";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FilePreview } from "@/components/molecules/FilePreview";
import { api } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { oversize } from "@/features/work-plans/uploadService";
import { useDeactivateWorkType, useSaveWorkType, useWorkTypes, type WorkType } from "../workTypeService";

const schema = z.object({
  name: z.string().trim().min(1, "Nama jenis pekerjaan wajib diisi."),
  photos: z
    .array(
      z.object({
        label: z.string().trim().min(1, "Label slot wajib diisi."),
        hint: z.string().trim(),
        required: z.boolean(),
        example_file_id: z.string().nullable(),
      }),
    )
    .refine((slots) => new Set(slots.map((s) => s.label.trim().toLowerCase())).size === slots.length, {
      message: "Label slot tidak boleh kembar.",
    }),
});
type Values = z.infer<typeof schema>;

/** Jenis pekerjaan + template foto laporan (T9): GET/POST/PUT/DELETE /work-types, izin create:plan (PM/OPS). */
export function WorkTypesPage() {
  const types = useWorkTypes(true);
  const [editing, setEditing] = useState<WorkType | "new" | null>(null);
  const [removing, setRemoving] = useState<WorkType | null>(null);

  return (
    <>
      <PageHeader title="Jenis pekerjaan" action={<Button onClick={() => setEditing("new")}>Tambah jenis</Button>} />

      {types.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      )}
      {types.isError && (
        <div role="alert" className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <p className="mb-3 text-danger">Jenis pekerjaan tidak dapat dimuat.</p>
          <Button variant="outline" onClick={() => types.refetch()}>
            Coba lagi
          </Button>
        </div>
      )}
      {types.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <p className="mb-3 text-mist">Belum ada jenis pekerjaan. Tambahkan jenis beserta template foto laporannya.</p>
          <Button onClick={() => setEditing("new")}>Tambah jenis</Button>
        </div>
      )}
      {types.data && types.data.length > 0 && (
        <ul className="grid gap-3 md:grid-cols-2">
          {types.data.map((t) => (
            <li key={t.id} className="rounded-panel border border-line bg-surface p-4 shadow-card">
              <div className="mb-2 flex items-start justify-between gap-2">
                <p className="font-medium">{t.name}</p>
                {!t.is_active && <span className="rounded-control bg-hover px-2 py-0.5 text-xs text-mist">Nonaktif</span>}
              </div>
              {t.photos.length === 0 ? (
                <p className="text-sm text-mist">Tanpa template foto.</p>
              ) : (
                <ol className="list-decimal space-y-0.5 pl-5 text-sm">
                  {t.photos.map((p) => (
                    <li key={p.id}>
                      {p.label}
                      {p.required && <span className="ml-1 text-xs text-danger">wajib</span>}
                      {p.example_file_id && <span className="ml-1 text-xs text-mist">· ada foto contoh</span>}
                      {p.hint && <span className="block text-xs text-mist">{p.hint}</span>}
                    </li>
                  ))}
                </ol>
              )}
              <div className="mt-3 flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setEditing(t)}>
                  Ubah
                </Button>
                {t.is_active && (
                  <Button variant="ghost" size="sm" onClick={() => setRemoving(t)} aria-label={`Nonaktifkan ${t.name}`}>
                    Nonaktifkan
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {editing && <WorkTypeDialog type={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
      {removing && <DeactivateDialog type={removing} onClose={() => setRemoving(null)} />}
    </>
  );
}

function WorkTypeDialog({ type, onClose }: { type: WorkType | null; onClose: () => void }) {
  const save = useSaveWorkType(type?.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: type?.name ?? "",
      photos: (type?.photos ?? []).map((p) => ({ label: p.label, hint: p.hint ?? "", required: p.required ?? false, example_file_id: p.example_file_id ?? null })),
    },
  });
  const slots = useFieldArray({ control, name: "photos" });
  const watched = useWatch({ control, name: "photos" });
  const [uploading, setUploading] = useState<number | null>(null);
  const uploadExample = async (i: number, file: File | undefined) => {
    if (!file) return;
    const big = oversize([file]);
    if (!file.type.startsWith("image/")) return setFormError("Foto contoh harus berupa gambar (JPG atau PNG).");
    if (big) return setFormError(big);
    setFormError(null);
    setUploading(i);
    try {
      const form = new FormData();
      form.set("file", file);
      const id = (await api.post<{ file_id: string }>("/files/upload", form)).data.file_id;
      setValue(`photos.${i}.example_file_id`, id, { shouldDirty: true });
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setUploading(null);
    }
  };

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await save.mutateAsync({
        name: v.name,
        photos: v.photos.map((p) => ({ label: p.label, hint: p.hint || null, required: p.required, example_file_id: p.example_file_id })),
      });
      toast.success(type ? "Jenis pekerjaan disimpan." : "Jenis pekerjaan ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });

  return (
    <VmsDialog
      open
      title={type ? "Ubah jenis pekerjaan" : "Tambah jenis pekerjaan"}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" form="work-type-form" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan"}
          </Button>
        </>
      }
    >
      <form id="work-type-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <TextField label="Nama jenis" error={errors.name?.message} {...register("name")} />
        <p className="mb-2 text-sm font-medium">Template foto laporan</p>
        {errors.photos?.root?.message && <p className="mb-2 text-sm text-danger">{errors.photos.root.message}</p>}
        <ol className="space-y-3">
          {slots.fields.map((slot, i) => (
            <li key={slot.id} className="rounded-control border border-line p-3">
              <TextField label={`Slot ${i + 1}`} error={errors.photos?.[i]?.label?.message} {...register(`photos.${i}.label`)} />
              <TextField label="Petunjuk (opsional)" {...register(`photos.${i}.hint`)} />
              <div className="mb-2">
                <p className="mb-1 text-sm font-medium">Foto contoh (opsional)</p>
                {watched?.[i]?.example_file_id ? (
                  <div className="flex items-center gap-3">
                    <FilePreview fileId={watched[i].example_file_id as string} fileName={`Contoh ${slot.label || i + 1}`} />
                    <Button type="button" variant="ghost" size="sm" onClick={() => setValue(`photos.${i}.example_file_id`, null, { shouldDirty: true })}>
                      Hapus contoh
                    </Button>
                  </div>
                ) : (
                  <input
                    type="file"
                    accept="image/jpeg,image/png"
                    aria-label={`Unggah foto contoh slot ${i + 1}`}
                    disabled={uploading === i}
                    className="block min-h-11 w-full text-sm file:mr-3 file:rounded-control file:border file:border-line file:bg-surface file:px-3 file:py-2"
                    onChange={(e) => {
                      void uploadExample(i, e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                )}
                {uploading === i && <p className="text-xs text-mist">Mengunggah...</p>}
              </div>
              <label className="mb-2 flex min-h-11 items-center gap-2 text-sm">
                <input type="checkbox" className="size-5" {...register(`photos.${i}.required`)} />
                Wajib diisi sebelum laporan dikirim
              </label>
              <div className="flex gap-2">
                <Button type="button" variant="outline" size="sm" disabled={i === 0} onClick={() => slots.move(i, i - 1)} aria-label={`Naikkan slot ${i + 1}`}>
                  <ArrowUp className="size-4" />
                </Button>
                <Button type="button" variant="outline" size="sm" disabled={i === slots.fields.length - 1} onClick={() => slots.move(i, i + 1)} aria-label={`Turunkan slot ${i + 1}`}>
                  <ArrowDown className="size-4" />
                </Button>
                <Button type="button" variant="ghost" size="sm" onClick={() => slots.remove(i)} aria-label={`Hapus slot ${i + 1}`}>
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </li>
          ))}
        </ol>
        <Button type="button" variant="outline" className="mt-3 w-full" onClick={() => slots.append({ label: "", hint: "", required: false, example_file_id: null })}>
          <Plus className="size-4" /> Tambah slot foto
        </Button>
      </form>
    </VmsDialog>
  );
}

function DeactivateDialog({ type, onClose }: { type: WorkType; onClose: () => void }) {
  const remove = useDeactivateWorkType();
  const confirm = async () => {
    try {
      await remove.mutateAsync(type.id);
      toast.success("Jenis pekerjaan dinonaktifkan.");
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <VmsDialog
      open
      title="Nonaktifkan jenis pekerjaan?"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={remove.isPending}>
            Batal
          </Button>
          <Button variant="destructive" onClick={confirm} disabled={remove.isPending}>
            Nonaktifkan
          </Button>
        </>
      }
    >
      <p className="text-sm">
        <strong className="text-ink">{type.name}</strong> tidak akan ditawarkan lagi untuk rencana kerja baru. Rencana kerja yang
        sudah memakainya tetap utuh.
      </p>
    </VmsDialog>
  );
}
