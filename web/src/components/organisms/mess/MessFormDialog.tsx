import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextField, SelectField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { useCreateMessStay, useMessPlaces } from "@/services/messService";
import { useEmployees } from "@/services/employeeService";

const messSchema = z
  .object({
    employee_id: z.string().trim().min(1, "Karyawan wajib dipilih."),
    mess_id: z.string().trim().min(1, "Mess wajib dipilih."),
    stay_start_date: z
      .string()
      .trim()
      .min(1, "Tanggal mulai inap wajib diisi."),
    stay_end_date: z
      .string()
      .trim()
      .min(1, "Tanggal selesai inap wajib diisi."),
  })
  .refine(
    (v) =>
      !v.stay_start_date ||
      !v.stay_end_date ||
      v.stay_end_date >= v.stay_start_date,
    {
      message: "Tanggal selesai tidak boleh sebelum tanggal mulai.",
      path: ["stay_end_date"],
    },
  );
type MessValues = z.infer<typeof messSchema>;

/** HR/GA menempatkan karyawan: mess dipilih dari daftar (bukan diketik), langsung disetujui. */
export function MessFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateMessStay();
  const places = useMessPlaces();
  const employeesQuery = useEmployees({ status: "active", page: 1, size: 100 });
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<MessValues>({
    resolver: zodResolver(messSchema),
    defaultValues: {
      employee_id: "",
      mess_id: "",
      stay_start_date: "",
      stay_end_date: "",
    },
  });

  const employeeList = employeesQuery.data?.items ?? [];
  const placeList = places.data ?? [];

  const onSubmit = async (values: MessValues) => {
    setFormError(null);
    try {
      await create.mutateAsync(values);
      toast.success("Hunian mess berhasil dicatat.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };

  return (
    <VmsDialog
      open
      title="Tempatkan Karyawan di Mess"
      onClose={onClose}
      footer={
        <DialogActions
          onCancel={onClose}
          busy={isSubmitting}
          formId="mess-form"
        />
      }
    >
      <FormBlock id="mess-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}

        <SelectField
          label="Karyawan yang Menempati"
          error={errors.employee_id?.message}
          {...register("employee_id")}
        >
          <ControlOption value="">-- Pilih Karyawan --</ControlOption>
          {employeeList.map((emp) => (
            <ControlOption key={emp.employee_id} value={emp.employee_id}>
              {emp.full_name} ({emp.employee_no || "Karyawan"})
            </ControlOption>
          ))}
        </SelectField>

        <SelectField
          label="Mess"
          error={errors.mess_id?.message}
          {...register("mess_id")}
        >
          <ControlOption value="">-- Pilih Mess --</ControlOption>
          {placeList.map((p) => (
            <ControlOption key={p.mess_id} value={p.mess_id}>
              {p.mess_name} · {p.city}
              {p.capacity ? ` (${p.occupied}/${p.capacity} terisi)` : ""}
            </ControlOption>
          ))}
        </SelectField>
        {places.isSuccess && placeList.length === 0 && (
          <TextBlock className="text-xs text-mist">
            Belum ada mess terdaftar. Tambahkan dulu di tab “Daftar Mess”.
          </TextBlock>
        )}

        <div className="grid grid-cols-2 gap-2">
          <TextField
            label="Tanggal Mulai Inap"
            type="date"
            error={errors.stay_start_date?.message}
            {...register("stay_start_date")}
          />
          <TextField
            label="Tanggal Selesai Inap"
            type="date"
            error={errors.stay_end_date?.message}
            {...register("stay_end_date")}
          />
        </div>
      </FormBlock>
    </VmsDialog>
  );
}
