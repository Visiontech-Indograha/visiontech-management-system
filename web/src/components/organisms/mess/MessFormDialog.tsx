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
import { useCreateMessStay } from "@/services/messService";

const messSchema = z.object({
  employee_id: z.string().trim().min(1, "ID Karyawan wajib diisi."),
  mess_name: z.string().trim().min(1, "Nama mess wajib diisi."),
  room_number: z.string().trim().optional(),
  check_in_date: z.string().trim().min(1, "Tanggal check-in wajib diisi."),
  notes: z.string().trim().optional(),
});
type MessValues = z.infer<typeof messSchema>;

export function MessFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateMessStay();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<MessValues>({
    resolver: zodResolver(messSchema),
    defaultValues: {
      employee_id: "",
      mess_name: "",
      room_number: "",
      check_in_date: "",
      notes: "",
    },
  });

  const onSubmit = async (values: MessValues) => {
    setFormError(null);
    try {
      await create.mutateAsync({
        employee_id: values.employee_id,
        mess_name: values.mess_name,
        room_number: values.room_number,
        check_in_date: values.check_in_date,
        notes: values.notes,
      });
      toast.success("Hunian mess berhasil didaftarkan.");
      onClose();
    } catch {
      setFormError("Gagal mendaftarkan hunian mess.");
    }
  };

  return (
    <VmsDialog
      open
      title="Check In Mess Karyawan"
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={isSubmitting} formId="mess-form" />}
    >
      <FormBlock id="mess-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}
        <TextField
          label="ID Karyawan"
          placeholder="UUID Karyawan"
          error={errors.employee_id?.message}
          {...register("employee_id")}
        />
        <TextField
          label="Nama Mess"
          placeholder="Misal: Mess Duri Sektor Timur"
          error={errors.mess_name?.message}
          {...register("mess_name")}
        />
        <TextField
          label="Nomor Kamar"
          placeholder="Misal: B-02"
          error={errors.room_number?.message}
          {...register("room_number")}
        />
        <TextField
          label="Tanggal Check In"
          type="date"
          error={errors.check_in_date?.message}
          {...register("check_in_date")}
        />
        <TextField
          label="Catatan"
          placeholder="Fasilitas tambahan atau keterangan"
          error={errors.notes?.message}
          {...register("notes")}
        />
      </FormBlock>
    </VmsDialog>
  );
}
