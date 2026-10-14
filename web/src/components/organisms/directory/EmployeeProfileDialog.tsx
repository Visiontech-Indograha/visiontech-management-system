import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { ATTENDANCE_MODE_LABEL } from "@/lib/attendanceModeLabels";
import { useUpdateEmployee, type Employee, type EmployeeUpdate } from "@/services/employeeService";
import { oversize, uploadForm } from "@/services/uploadService";
import { useFileUrl } from "@/hooks/useFileUrl";
import { ControlInput, ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { Camera, Trash2, User } from "@/components/molecules/Glyphs";
import { AvatarBlock, AvatarBlockFallback, AvatarBlockImage } from "@/components/molecules/AvatarBlock";

const optional = z.string().trim();
const profileSchema = z.object({
  full_name: z.string().trim().min(1, "Nama wajib diisi."),
  email: z.union([z.literal(""), z.string().trim().email("Format email tidak valid.")]),
  phone: optional.max(30, "No. telepon maksimal 30 karakter."),
  birth_date: optional,
  address: optional,
  attendance_mode: z.enum(["FIELD", "OFFICE"], "Pilih cara absen."),
});
type ProfileValues = z.infer<typeof profileSchema>;
const FIELDS = ["full_name", "email", "phone", "birth_date", "address", "attendance_mode"] as const;

/** Dialog "Ubah profil" karyawan (PATCH/PUT /employees/{id}). */
export function EmployeeProfileDialog({ employee, onClose }: { employee: Employee; onClose: () => void }) {
  const update = useUpdateEmployee(employee.id);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { data: currentPhotoUrl } = useFileUrl(employee.photo_file_id, "view");

  const [formError, setFormError] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [removePhoto, setRemovePhoto] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: employee.full_name,
      email: employee.email ?? "",
      phone: employee.phone ?? "",
      birth_date: employee.birth_date ?? "",
      address: employee.address ?? "",
      attendance_mode: employee.attendance_mode ?? "FIELD",
    },
  });

  const fullNameValue = useWatch({ control, name: "full_name" });

  useEffect(() => {
    return () => {
      if (photoPreview) URL.revokeObjectURL(photoPreview);
    };
  }, [photoPreview]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setFormError("Berkas foto profil harus berupa gambar (JPG, PNG, atau WebP).");
      return;
    }

    const sizeErr = oversize([file]);
    if (sizeErr) {
      setFormError(sizeErr);
      return;
    }

    setFormError(null);
    setPhotoFile(file);
    setRemovePhoto(false);
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoPreview(URL.createObjectURL(file));
  };

  const handleRemovePhoto = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoFile(null);
    setPhotoPreview(null);
    setRemovePhoto(true);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      let finalPhotoId: string | null | undefined = undefined;
      if (photoFile) {
        setUploadingPhoto(true);
        const form = new FormData();
        form.set("file", photoFile);
        finalPhotoId = await uploadForm(form);
      } else if (removePhoto) {
        finalPhotoId = null;
      }

      const body: EmployeeUpdate = {
        full_name: v.full_name,
        email: v.email || null,
        phone: v.phone || null,
        birth_date: v.birth_date || null,
        address: v.address || null,
        attendance_mode: v.attendance_mode,
        ...(finalPhotoId !== undefined ? { photo_file_id: finalPhotoId } : {}),
      };

      await update.mutateAsync(body);
      toast.success("Profil berhasil diperbarui.");
      onClose();
    } catch (err) {
      const fields = err instanceof ApiError ? ((err.details.fields ?? {}) as Record<string, string>) : {};
      const known = FIELDS.filter((f) => fields[f]);
      if (known.length) known.forEach((f) => setError(f, { message: fields[f] }));
      else setFormError(err instanceof ApiError ? err.message : errorMessage(err));
    } finally {
      setUploadingPhoto(false);
    }
  });

  const isBusy = isSubmitting || uploadingPhoto;
  const displayPhotoUrl = photoPreview ?? (removePhoto ? null : currentPhotoUrl);

  return (
    <VmsDialog
      open
      title="Ubah profil"
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={isBusy} formId="profile-form" />}
    >
      <FormBlock id="profile-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />

        {/* Foto Profil */}
        <div className="mb-6 flex flex-col items-center gap-3 rounded-lg border border-line bg-surface/50 p-4 sm:flex-row">
          <AvatarBlock className="h-20 w-20 ring-2 ring-primary/20">
            {displayPhotoUrl ? (
              <AvatarBlockImage src={displayPhotoUrl} alt="Foto Profil" className="object-cover" />
            ) : null}
            <AvatarBlockFallback className="bg-muted text-muted-foreground">
              {fullNameValue ? fullNameValue.charAt(0).toUpperCase() : <User className="h-8 w-8" />}
            </AvatarBlockFallback>
          </AvatarBlock>

          <div className="flex flex-1 flex-col items-center gap-2 sm:items-start">
            <TextBlock className="text-sm font-medium">Foto Profil</TextBlock>
            <TextBlock className="text-xs text-mist">
              Format JPG, PNG, atau WebP. Maksimal ukuran 10 MB.
            </TextBlock>
            <div className="flex items-center gap-2">
              <ControlInput
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleFileChange}
                disabled={isBusy}
              />
              <ActionButton
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={isBusy}
              >
                <Camera className="mr-1.5 h-4 w-4" />
                {displayPhotoUrl ? "Ganti foto" : "Pilih foto"}
              </ActionButton>
              {displayPhotoUrl && (
                <ActionButton
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleRemovePhoto}
                  disabled={isBusy}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="mr-1.5 h-4 w-4" />
                  Hapus
                </ActionButton>
              )}
            </div>
          </div>
        </div>

        <TextField label="Nama lengkap" error={errors.full_name?.message} {...register("full_name")} />
        <TextField label="Email" type="email" error={errors.email?.message} {...register("email")} />
        <TextField label="No. telepon" error={errors.phone?.message} {...register("phone")} />
        <TextField label="Tanggal lahir" type="date" error={errors.birth_date?.message} {...register("birth_date")} />
        <TextAreaField label="Alamat" error={errors.address?.message} {...register("address")} />
        <SelectField label="Absen lewat" error={errors.attendance_mode?.message} {...register("attendance_mode")}>
          <ControlOption value="FIELD">{ATTENDANCE_MODE_LABEL.FIELD}</ControlOption>
          <ControlOption value="OFFICE">{ATTENDANCE_MODE_LABEL.OFFICE}</ControlOption>
        </SelectField>
      </FormBlock>
    </VmsDialog>
  );
}
