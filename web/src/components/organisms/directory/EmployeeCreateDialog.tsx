import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { SelectField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useCreateEmployee, useUnits } from "@/services/employeeService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";

const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());

const createSchema = z.object({
  employee_no: z.string().trim().min(1, "No. karyawan wajib diisi."),
  full_name: z.string().trim().min(1, "Nama lengkap wajib diisi."),
  position: z.string().trim().min(1, "Jabatan wajib diisi."),
  unit_id: z.string().min(1, "Pilih unit."),
  join_date: z.string().min(1, "Tanggal bergabung wajib diisi."),
  email: z.union([z.literal(""), z.string().trim().email("Format email tidak valid.")]),
  phone: z.string().trim(),
});

type CreateValues = z.infer<typeof createSchema>;

/** M2-03 · HR mendaftarkan karyawan baru (prototipe "Tambah karyawan"). */
export function EmployeeCreateDialog({ onClose }: { onClose: () => void }) {
  const units = useUnits();
  const create = useCreateEmployee();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { employee_no: "", full_name: "", position: "", unit_id: "", join_date: today(), email: "", phone: "" },
  });

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      const created = await create.mutateAsync({ ...v, email: v.email || null, phone: v.phone || null });
      toast.success("Karyawan baru tersimpan.");
      onClose();
      navigate(`/directory/${created.id}`);
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });

  return (
    <VmsDialog
      open
      title="Tambah karyawan"
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="create-employee-form" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan"}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="create-employee-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
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
        <TextField label="Email (opsional)" type="email" error={errors.email?.message} {...register("email")} />
        <TextField label="No. telepon (opsional)" error={errors.phone?.message} {...register("phone")} />
      </FormBlock>
    </VmsDialog>
  );
}
