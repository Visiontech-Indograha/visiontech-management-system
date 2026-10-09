import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { SelectField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { usePromoteEmployee, useUnits, type Employee } from "@/services/employeeService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";

const schema = z.object({
  position: z.string().trim().min(1, "Jabatan wajib diisi."),
  unit_id: z.string().min(1, "Pilih unit."),
  valid_from: z.string().min(1, "Tanggal berlaku wajib diisi."),
});

type Values = z.infer<typeof schema>;

const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());

/**
 * HR: mutasi/promosi (domain.js PROMOTE). API menolak mutasi lintas unit selama karyawan masih
 * bertugas di SK aktif — pesannya ditampilkan apa adanya.
 */
export function EmployeePromoteDialog({ employee, onClose }: { employee: Employee; onClose: () => void }) {
  const units = useUnits();
  const promote = usePromoteEmployee(employee.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { position: employee.position, unit_id: employee.unit_id ?? "", valid_from: today() },
  });

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await promote.mutateAsync(v);
      toast.success("Penempatan baru berlaku. Riwayat lama tetap tersimpan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });

  return (
    <VmsDialog
      open
      title="Mutasi / promosi"
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="promote-form" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan"}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="promote-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <TextBlock role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </TextBlock>
        )}
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
        <TextField label="Berlaku mulai" type="date" error={errors.valid_from?.message} {...register("valid_from")} />
      </FormBlock>
    </VmsDialog>
  );
}
