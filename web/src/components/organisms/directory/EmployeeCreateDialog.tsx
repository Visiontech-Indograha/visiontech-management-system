import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useRef, useState } from "react";
import { useForm, useWatch, type Control, type UseFormRegister } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { useCreateEmployee, useNextEmployeeNo } from "@/services/employeeService";
import { oversize, uploadForm } from "@/services/uploadService";
import { ControlInput, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { DialogActions } from "@/components/molecules/DialogActions";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { Camera, Trash2, User } from "@/components/molecules/Glyphs";
import { EmployeeFormFields } from "./EmployeeFormFields";
import { employeeFormSchema, type EmployeeFormValues } from "@/lib/employeeForm";
import { AvatarBlock, AvatarBlockFallback, AvatarBlockImage } from "@/components/molecules/AvatarBlock";

const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());

const createSchema = employeeFormSchema.and(
  z.object({ address_line: z.string().trim().max(255, "Alamat maksimal 255 karakter."), city: z.string().trim().max(100, "Kota maksimal 100 karakter."), postal_code: z.string().trim().max(10, "Kode pos maksimal 10 karakter.") }),
);
type CreateValues = z.infer<typeof createSchema>;

/** HR mendaftarkan karyawan baru V2: data kerja, foto, dan alamat pertama (opsional). */
export function EmployeeCreateDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateEmployee();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [formError, setFormError] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    setError,
    setValue,
    getValues,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      employee_no: "",
      full_name: "",
      office_id: "",
      division_id: "",
      position_id: "",
      join_date: today(),
      pkwt_end_date: "",
      address_line: "",
      city: "",
      postal_code: "",
    },
  });
  const nextNo = useNextEmployeeNo();
  useEffect(() => {
    // Isi otomatis (tetap bisa diubah); jangan menimpa ketikan pengguna.
    if (nextNo.data && !getValues("employee_no")) setValue("employee_no", nextNo.data, { shouldDirty: false });
  }, [nextNo.data, getValues, setValue]);

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
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoPreview(URL.createObjectURL(file));
  };

  const handleRemovePhoto = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoFile(null);
    setPhotoPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      let photo_file_id: string | null = null;
      if (photoFile) {
        setUploadingPhoto(true);
        const form = new FormData();
        form.set("file", photoFile);
        photo_file_id = await uploadForm(form);
      }

      const anyAddressField = !!(v.address_line || v.city || v.postal_code);
      if (anyAddressField && (!v.address_line || !v.city || !v.postal_code)) {
        setFormError("Jika mengisi alamat, seluruh kolom (jalan, kota, dan kode pos) wajib diisi lengkap.");
        return;
      }
      const hasAddress = !!(v.address_line && v.city && v.postal_code);
      const created = await create.mutateAsync({
        employee_no: v.employee_no,
        full_name: v.full_name,
        office_id: v.office_id,
        division_id: v.division_id || null,
        position_id: v.position_id || null,
        join_date: v.join_date,
        pkwt_end_date: v.pkwt_end_date || null,
        photo_file_id,
        address: hasAddress ? { address_line: v.address_line, city: v.city, postal_code: v.postal_code } : null,
      });

      toast.success("Karyawan baru berhasil ditambahkan.");
      onClose();
      navigate(`/directory/${created.employee_id}`);
    } catch (err) {
      setFormError(applyFieldErrors(err, setError) ? "Periksa kolom yang ditandai." : errorMessage(err));
    } finally {
      setUploadingPhoto(false);
    }
  });

  const isBusy = isSubmitting || uploadingPhoto;

  return (
    <VmsDialog dirty={isDirty}
      open
      title="Tambah karyawan"
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={isBusy} formId="create-employee-form" />}
    >
      <FormBlock id="create-employee-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />

        {/* Foto Profil */}
        <div className="mb-6 flex flex-col items-center gap-3 rounded-lg border border-line bg-surface/50 p-4 sm:flex-row">
          <AvatarBlock className="h-20 w-20 ring-2 ring-primary/20">
            {photoPreview ? (
              <AvatarBlockImage src={photoPreview} alt="Pratinjau Foto" className="object-cover" />
            ) : null}
            <AvatarBlockFallback className="bg-muted text-muted-foreground">
              {fullNameValue ? fullNameValue.charAt(0).toUpperCase() : <User className="h-8 w-8" />}
            </AvatarBlockFallback>
          </AvatarBlock>

          <div className="flex flex-1 flex-col items-center gap-2 sm:items-start">
            <TextBlock className="text-sm font-medium">Foto Profil (Opsional)</TextBlock>
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
                {photoFile ? "Ganti foto" : "Pilih foto"}
              </ActionButton>
              {photoFile && (
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

        <EmployeeFormFields
          register={register as unknown as UseFormRegister<EmployeeFormValues>}
          errors={errors}
          control={control as unknown as Control<EmployeeFormValues>}
        />
        <TextBlock className="mt-6 mb-2 font-semibold text-sm text-foreground">Alamat (Opsional)</TextBlock>
        <TextField label="Alamat" maxLength={255} error={errors.address_line?.message} {...register("address_line")} />
        <TextField label="Kota" maxLength={100} error={errors.city?.message} {...register("city")} />
        <TextField label="Kode pos" maxLength={10} error={errors.postal_code?.message} {...register("postal_code")} />
      </FormBlock>
    </VmsDialog>
  );
}
