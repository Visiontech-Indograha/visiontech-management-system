import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useOffboardEmployee, type Employee } from "@/services/employeeService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";

const offboardSchema = z.object({ reason: z.string().trim().min(1, "Alasan pengakhiran masa kerja wajib diisi.") });

/**
 * M2-02 · HR mengakhiri masa kerja (domain.js OFFBOARD): alasan wajib, akses login dicabut, data historis
 * tetap. API menolak bila karyawan masih bertugas di SK berjalan — pesannya ditampilkan apa adanya.
 */
export function EmployeeOffboardDialog({ employee, onClose }: { employee: Employee; onClose: () => void }) {
  const offboard = useOffboardEmployee(employee.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ reason: string }>({ resolver: zodResolver(offboardSchema), defaultValues: { reason: "" } });

  const onSubmit = handleSubmit(async ({ reason }) => {
    setFormError(null);
    try {
      await offboard.mutateAsync(reason.trim());
      toast.success("Masa kerja diakhiri dan akses dicabut. Data historis tetap tersedia.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });

  return (
    <VmsDialog
      open
      title={`Offboarding ${employee.full_name}`}
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="offboard-form" variant="destructive" disabled={isSubmitting}>
            {isSubmitting ? "Memproses..." : "Akhiri masa kerja"}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="offboard-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <TextBlock className="mb-4 text-sm text-mist">
          Akun login karyawan ini dinonaktifkan. Riwayat rencana kerja, absensi, dan dokumen tetap tersimpan.
        </TextBlock>
        <TextField label="Alasan" error={errors.reason?.message} {...register("reason")} />
      </FormBlock>
    </VmsDialog>
  );
}
