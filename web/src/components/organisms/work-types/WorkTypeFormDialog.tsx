import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { FilePreview } from "@/components/molecules/FilePreview";
import { SelectField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { workTypeSchema, type WorkTypeValues } from "@/schemas/workTypeSchema";
import { oversize, uploadForm } from "@/services/uploadService";
import { useSaveWorkType, type WorkType } from "@/services/workTypeService";
import { useDivisions } from "@/services/employeeService";
import { useSession } from "@/stores/sessionStore";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "@/components/molecules/Glyphs";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ControlInput, ControlLabel, ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";

/** Dialog tambah/ubah jenis pekerjaan: nama + divisi + slot template foto (label, petunjuk, foto contoh, wajib, urutan). */
export function WorkTypeFormDialog({ type, onClose }: { type: WorkType | null; onClose: () => void }) {
  const save = useSaveWorkType(type?.id);
  const { me } = useSession();
  const { data: units } = useDivisions();
  const [formError, setFormError] = useState<string | null>(null);

  const initialDivisionId = type?.division_id ?? me?.division_id ?? "";

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
      division_id: initialDivisionId,
      description: type?.description ?? "",
      photos: (type?.photos ?? []).map((p) => ({
        label: p.label,
        hint: p.hint ?? "",
        required: p.required ?? false,
        example_file_id: p.example_file_id ?? null,
      })),
    },
  });

  useEffect(() => {
    const divId = type?.division_id ?? me?.division_id;
    if (divId) {
      setValue("division_id", divId);
    }
  }, [type, me, units, setValue]);
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
      const id = await uploadForm(form);
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
      const divisionId = v.division_id || me?.division_id || type?.division_id || undefined;
      await save.mutateAsync({
        name: v.name,
        division_id: divisionId,
        description: v.description || null,
        photos: v.photos.map((p) => ({
          label: p.label,
          hint: p.hint || null,
          required: p.required,
          example_file_id: p.example_file_id,
        })),
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
        <DialogActions onCancel={onClose} busy={isSubmitting} formId="work-type-form" />
      }
    >
      <FormBlock id="work-type-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <SelectField
          label="Divisi"
          error={errors.division_id?.message}
          hint={
            me?.role === "PROJECT_MANAGER" && me?.division_id
              ? "Divisi ditentukan otomatis sesuai akun Anda."
              : "Pilih divisi yang menaungi jenis pekerjaan ini."
          }
          disabled={Boolean(me?.role === "PROJECT_MANAGER" && me?.division_id)}
          {...register("division_id")}
        >
          <ControlOption value="">-- Pilih Divisi --</ControlOption>
          {units?.map((u) => (
            <ControlOption key={u.id} value={u.id}>
              {`${u.name} (${u.code})`}
            </ControlOption>
          ))}
          {initialDivisionId && !units?.some((u) => u.id === initialDivisionId) && (
            <ControlOption value={initialDivisionId}>
              {type?.division_name || "Divisi Terkait"}
            </ControlOption>
          )}
        </SelectField>
        <TextField label="Nama jenis" error={errors.name?.message} {...register("name")} />
        <TextField label="Keterangan (opsional)" error={errors.description?.message} {...register("description")} />
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
