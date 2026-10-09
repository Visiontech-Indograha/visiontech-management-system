import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { Button } from "@/components/atoms/Button";
import { FilePreview } from "@/components/molecules/FilePreview";
import { TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { api } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { workTypeSchema, type WorkTypeValues } from "@/schemas/workTypeSchema";
import { oversize } from "@/services/uploadService";
import { useSaveWorkType, type WorkType } from "@/services/workTypeService";

/** Dialog tambah/ubah jenis pekerjaan: nama + slot template foto (label, petunjuk, foto contoh, wajib, urutan). */
export function WorkTypeFormDialog({ type, onClose }: { type: WorkType | null; onClose: () => void }) {
  const save = useSaveWorkType(type?.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<WorkTypeValues>({
    resolver: zodResolver(workTypeSchema),
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
