import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { FilePreview } from "@/components/molecules/FilePreview";
import { TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { api } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { workTypeSchema, type WorkTypeValues } from "@/schemas/workTypeSchema";
import { oversize } from "@/services/uploadService";
import { useSaveWorkType, type WorkType } from "@/services/workTypeService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "@/components/molecules/Glyphs";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ControlInput, ControlLabel, FormBlock } from "@/components/molecules/FormBlock";

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
          <ActionButton variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="work-type-form" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan"}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="work-type-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <TextBlock role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </TextBlock>
        )}
        <TextField label="Nama jenis" error={errors.name?.message} {...register("name")} />
        <TextBlock className="mb-2 text-sm font-medium">Template foto laporan</TextBlock>
        {errors.photos?.root?.message && <TextBlock className="mb-2 text-sm text-danger">{errors.photos.root.message}</TextBlock>}
        <ListBlock as="ol" className="space-y-3">
          {slots.fields.map((slot, i) => (
            <ListEntry key={slot.id} className="rounded-control border border-line p-3">
              <TextField label={`Slot ${i + 1}`} error={errors.photos?.[i]?.label?.message} {...register(`photos.${i}.label`)} />
              <TextField label="Petunjuk (opsional)" {...register(`photos.${i}.hint`)} />
              <div className="mb-2">
                <TextBlock className="mb-1 text-sm font-medium">Foto contoh (opsional)</TextBlock>
                {watched?.[i]?.example_file_id ? (
                  <div className="flex items-center gap-3">
                    <FilePreview fileId={watched[i].example_file_id as string} fileName={`Contoh ${slot.label || i + 1}`} />
                    <ActionButton type="button" variant="ghost" size="sm" onClick={() => setValue(`photos.${i}.example_file_id`, null, { shouldDirty: true })}>
                      Hapus contoh
                    </ActionButton>
                  </div>
                ) : (
                  <ControlInput
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
                {uploading === i && <TextBlock className="text-xs text-mist">Mengunggah...</TextBlock>}
              </div>
              <ControlLabel className="mb-2 flex min-h-11 items-center gap-2 text-sm">
                <ControlInput type="checkbox" className="size-5" {...register(`photos.${i}.required`)} />
                Wajib diisi sebelum laporan dikirim
              </ControlLabel>
              <div className="flex gap-2">
                <ActionButton type="button" variant="outline" size="sm" disabled={i === 0} onClick={() => slots.move(i, i - 1)} aria-label={`Naikkan slot ${i + 1}`}>
                  <ArrowUp className="size-4" />
                </ActionButton>
                <ActionButton type="button" variant="outline" size="sm" disabled={i === slots.fields.length - 1} onClick={() => slots.move(i, i + 1)} aria-label={`Turunkan slot ${i + 1}`}>
                  <ArrowDown className="size-4" />
                </ActionButton>
                <ActionButton type="button" variant="ghost" size="sm" onClick={() => slots.remove(i)} aria-label={`Hapus slot ${i + 1}`}>
                  <Trash2 className="size-4" />
                </ActionButton>
              </div>
            </ListEntry>
          ))}
        </ListBlock>
        <ActionButton type="button" variant="outline" className="mt-3 w-full" onClick={() => slots.append({ label: "", hint: "", required: false, example_file_id: null })}>
          <Plus className="size-4" /> Tambah slot foto
        </ActionButton>
      </FormBlock>
    </VmsDialog>
  );
}
