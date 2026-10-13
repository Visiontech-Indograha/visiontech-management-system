import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { ATTENDANCE_MODE_LABEL } from "@/lib/attendanceModeLabels";
import { useCreateEmployee, useUnits } from "@/services/employeeService";
import { oversize, uploadForm } from "@/services/uploadService";
import { ControlInput, ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { DialogActions } from "@/components/molecules/DialogActions";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { Camera, Trash2, User } from "@/components/molecules/Glyphs";
import { AvatarBlock, AvatarBlockFallback, AvatarBlockImage } from "@/components/molecules/AvatarBlock";

const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());

const optional = z.string().trim();

const createSchema = z.object({
  employee_no: z.string().trim().min(1, "No. karyawan wajib diisi."),
  full_name: z.string().trim().min(1, "Nama lengkap wajib diisi."),
  position: z.string().trim().min(1, "Jabatan wajib diisi."),
  unit_id: z.string().min(1, "Pilih unit."),
  join_date: z.string().min(1, "Tanggal bergabung wajib diisi."),
  attendance_mode: z.enum(["FIELD", "OFFICE"]),
  birth_date: optional,
  email: z.union([z.literal(""), z.string().trim().email("Format email tidak valid.")]),
  phone: optional,
  address: optional,
  // Kontak darurat (terstruktur)
  emergency_name: optional,
  emergency_relationship: optional,
  emergency_phone: optional,
  emergency_address: optional,
});

type CreateValues = z.infer<typeof createSchema>;

const RELATIONSHIP_OPTIONS = [
  "Istri",
  "Suami",
  "Orang Tua",
  "Anak",
  "Saudara",
  "Kerabat",
  "Teman",
  "Lainnya",
] as const;

/** M2-03 · HR mendaftarkan karyawan baru lengkap dengan foto profil dan kontak darurat. */
export function EmployeeCreateDialog({ onClose }: { onClose: () => void }) {
  const units = useUnits();
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
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      employee_no: "",
      full_name: "",
      position: "",
      unit_id: "",
      join_date: today(),
      attendance_mode: "FIELD",
      birth_date: "",
      email: "",
      phone: "",
      address: "",
      emergency_name: "",
      emergency_relationship: "Keluarga",
      emergency_phone: "",
      emergency_address: "",
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

      // Siapkan kontak darurat terstruktur jika diisi
      const emergency_contacts =
        v.emergency_name && v.emergency_phone
          ? [
              {
                name: v.emergency_name,
                relationship: v.emergency_relationship || "Keluarga",
                phone: v.emergency_phone,
                address: v.emergency_address || null,
                is_primary: true,
              },
            ]
          : undefined;

      const created = await create.mutateAsync({
        employee_no: v.employee_no,
        full_name: v.full_name,
        position: v.position,
        unit_id: v.unit_id || null,
        join_date: v.join_date,
        attendance_mode: v.attendance_mode,
        birth_date: v.birth_date || null,
        email: v.email || null,
        phone: v.phone || null,
        address: v.address || null,
        photo_file_id: photo_file_id,
        emergency_contacts,
      });

      toast.success("Karyawan baru berhasil ditambahkan.");
      onClose();
      navigate(`/directory/${created.id}`);
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setUploadingPhoto(false);
    }
  });

  const isBusy = isSubmitting || uploadingPhoto;

  return (
    <VmsDialog
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

        {/* Data Pokok */}
        <TextBlock className="mb-2 font-semibold text-sm text-foreground">Data Pokok</TextBlock>
        <TextField label="No. karyawan" error={errors.employee_no?.message} {...register("employee_no")} />
        <TextField label="Nama lengkap" error={errors.full_name?.message} {...register("full_name")} />
        <TextField label="Jabatan" error={errors.position?.message} {...register("position")} />
        <SelectField label="Unit" error={errors.unit_id?.message} {...register("unit_id")}>
          <ControlOption value="" disabled>
            {units.isPending ? "Memuat unit..." : "Pilih unit"}
          </ControlOption>
          {units.data?.map((u) => (
            <ControlOption key={u.id} value={u.id}>
              {u.name}
            </ControlOption>
          ))}
        </SelectField>
        <TextField label="Tanggal bergabung" type="date" error={errors.join_date?.message} {...register("join_date")} />

        <SelectField label="Absen lewat" error={errors.attendance_mode?.message} {...register("attendance_mode")}>
          <ControlOption value="FIELD">{ATTENDANCE_MODE_LABEL.FIELD}</ControlOption>
          <ControlOption value="OFFICE">{ATTENDANCE_MODE_LABEL.OFFICE}</ControlOption>
        </SelectField>

        {/* Data Pribadi */}
        <TextBlock className="mt-6 mb-2 font-semibold text-sm text-foreground">Data Pribadi</TextBlock>
        <TextField label="Tanggal lahir (opsional)" type="date" error={errors.birth_date?.message} {...register("birth_date")} />
        <TextField label="Email (opsional)" type="email" error={errors.email?.message} {...register("email")} />
        <TextField label="No. telepon (opsional)" error={errors.phone?.message} {...register("phone")} />
        <TextAreaField label="Alamat (opsional)" error={errors.address?.message} {...register("address")} />

        {/* Kontak Darurat */}
        <TextBlock className="mt-6 mb-2 font-semibold text-sm text-foreground">Kontak Darurat (Opsional)</TextBlock>
        <TextField
          label="Nama kontak darurat"
          error={errors.emergency_name?.message}
          hint="Nama keluarga / kerabat yang dapat dihubungi"
          {...register("emergency_name")}
        />
        <SelectField label="Hubungan" error={errors.emergency_relationship?.message} {...register("emergency_relationship")}>
          {RELATIONSHIP_OPTIONS.map((rel) => (
            <ControlOption key={rel} value={rel}>
              {rel}
            </ControlOption>
          ))}
        </SelectField>
        <TextField
          label="No. telepon darurat"
          error={errors.emergency_phone?.message}
          {...register("emergency_phone")}
        />
        <TextAreaField
          label="Alamat kontak darurat (opsional)"
          error={errors.emergency_address?.message}
          {...register("emergency_address")}
        />
      </FormBlock>
    </VmsDialog>
  );
}
