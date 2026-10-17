import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { useCreateOffboarding } from "@/services/offboardingService";

const offboardingSchema = z.object({
  employee_id: z.string().trim().min(1, "ID Karyawan wajib diisi."),
  resignation_date: z.string().trim().min(1, "Tanggal pengunduran diri wajib diisi."),
  last_working_date: z.string().trim().min(1, "Hari kerja terakhir wajib diisi."),
  reason: z.string().trim().optional(),
});
type OffboardingValues = z.infer<typeof offboardingSchema>;

export function OffboardingFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateOffboarding();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OffboardingValues>({
    resolver: zodResolver(offboardingSchema),
    defaultValues: {
      employee_id: "",
      resignation_date: "",
      last_working_date: "",
      reason: "",
    },
  });

  const onSubmit = async (values: OffboardingValues) => {
    setFormError(null);
    try {
      await create.mutateAsync({
        employee_id: values.employee_id,
        resignation_date: values.resignation_date,
        last_working_date: values.last_working_date,
        reason: values.reason,
      });
      toast.success("Pengajuan offboarding berhasil dibuat.");
      onClose();
    } catch {
      setFormError("Gagal mengajukan offboarding.");
    }
  };

  return (
    <VmsDialog
      open
      title="Pengajuan Offboarding Karyawan"
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={isSubmitting} formId="offboarding-form" />}
    >
      <FormBlock id="offboarding-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}
        <TextField
          label="ID Karyawan"
          placeholder="UUID Karyawan"
          error={errors.employee_id?.message}
          {...register("employee_id")}
        />
        <TextField
          label="Tanggal Pengunduran Diri (Resign)"
          type="date"
          error={errors.resignation_date?.message}
          {...register("resignation_date")}
        />
        <TextField
          label="Hari Kerja Terakhir (Last Working Date)"
          type="date"
          error={errors.last_working_date?.message}
          {...register("last_working_date")}
        />
        <TextField
          label="Alasan Pengunduran Diri"
          placeholder="Alasan pribadi, karir baru, mutasi, dll."
          error={errors.reason?.message}
          {...register("reason")}
        />
      </FormBlock>
    </VmsDialog>
  );
}
