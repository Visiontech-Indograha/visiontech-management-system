import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/atoms/Button";
import { SelectField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { ATTENDANCE_MODE_LABEL } from "../attendanceModeLabels";
import { useUpdateEmployee, type Employee, type EmployeeUpdate } from "../employeeService";

const optional = z.string().trim();
const profileSchema = z.object({
  full_name: z.string().trim().min(1, "Nama wajib diisi."),
  email: z.union([z.literal(""), z.email("Format email tidak valid.")]),
  phone: optional.max(30, "No. telepon maksimal 30 karakter."),
  birth_date: optional,
  address: optional,
  emergency_contact: optional,
  attendance_mode: z.enum(["FIELD", "OFFICE"], "Pilih cara absen."),
});
type ProfileValues = z.infer<typeof profileSchema>;
const FIELDS = ["full_name", "email", "phone", "birth_date", "address", "emergency_contact", "attendance_mode"] as const;

/** Dialog "Ubah profil" karyawan (PATCH /employees/{id}); galat per field dari server dipetakan ke isian. */
export function EmployeeProfileDialog({ employee, onClose }: { employee: Employee; onClose: () => void }) {
  const update = useUpdateEmployee(employee.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: employee.full_name,
      email: employee.email ?? "",
      phone: employee.phone ?? "",
      birth_date: employee.birth_date ?? "",
      address: employee.address ?? "",
      emergency_contact: employee.emergency_contact ?? "",
      attendance_mode: employee.attendance_mode ?? "FIELD",
    },
  });

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    const body: EmployeeUpdate = {
      full_name: v.full_name,
      email: v.email || null,
      phone: v.phone || null,
      birth_date: v.birth_date || null,
      address: v.address || null,
      emergency_contact: v.emergency_contact || null,
      attendance_mode: v.attendance_mode,
    };
    try {
      await update.mutateAsync(body);
      toast.success("Profil disimpan.");
      onClose();
    } catch (err) {
      const fields = err instanceof ApiError ? ((err.details.fields ?? {}) as Record<string, string>) : {};
      const known = FIELDS.filter((f) => fields[f]);
      if (known.length) known.forEach((f) => setError(f, { message: fields[f] }));
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  });

  return (
    <VmsDialog
      open
      title="Ubah profil"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" form="profile-form" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan"}
          </Button>
        </>
      }
    >
      <form id="profile-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <TextField label="Nama lengkap" error={errors.full_name?.message} {...register("full_name")} />
        <TextField label="Email" type="email" error={errors.email?.message} {...register("email")} />
        <TextField label="No. telepon" error={errors.phone?.message} {...register("phone")} />
        <TextField label="Tanggal lahir" type="date" error={errors.birth_date?.message} {...register("birth_date")} />
        <TextField label="Alamat" error={errors.address?.message} {...register("address")} />
        <TextField label="Kontak darurat" error={errors.emergency_contact?.message} {...register("emergency_contact")} />
        <SelectField label="Absen lewat" error={errors.attendance_mode?.message} {...register("attendance_mode")}>
          <option value="FIELD">{ATTENDANCE_MODE_LABEL.FIELD}</option>
          <option value="OFFICE">{ATTENDANCE_MODE_LABEL.OFFICE}</option>
        </SelectField>
      </form>
    </VmsDialog>
  );
}
