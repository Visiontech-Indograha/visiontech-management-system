import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import {
  TextField,
  TextAreaField,
  SelectField,
} from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { useCreateMessStay } from "@/services/messService";
import { useEmployees } from "@/services/employeeService";

const messSchema = z
  .object({
    employee_id: z.string().trim().min(1, "Karyawan wajib dipilih."),
    mess_name: z
      .string()
      .trim()
      .min(2, "Nama mess minimal 2 karakter.")
      .max(150),
    city: z.string().trim().min(2, "Kota minimal 2 karakter.").max(100),
    address: z.string().trim().min(5, "Alamat lengkap wajib diisi.").max(500),
    latitude: z.number().min(-90).max(90),
    longitude: z.number().min(-180).max(180),
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

export function MessFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateMessStay();
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
      mess_name: "",
      city: "",
      address: "",
      latitude: 0,
      longitude: 0,
      stay_start_date: "",
      stay_end_date: "",
    },
  });

  const employeeList = employeesQuery.data?.items ?? [];

  const onSubmit = async (values: MessValues) => {
    setFormError(null);
    try {
      await create.mutateAsync({
        employee_id: values.employee_id,
        mess_name: values.mess_name,
        city: values.city,
        address: values.address,
        latitude: values.latitude,
        longitude: values.longitude,
        stay_start_date: values.stay_start_date,
        stay_end_date: values.stay_end_date,
      });
      toast.success("Hunian mess berhasil didaftarkan.");
      onClose();
    } catch {
      setFormError(
        "Gagal mendaftarkan hunian mess. Pastikan koordinat dan periode terisi dengan benar.",
      );
    }
  };

  return (
    <VmsDialog
      open
      title="Check In Mess Karyawan"
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

        <div className="grid grid-cols-2 gap-2">
          <TextField
            label="Nama Mess"
            placeholder="Misal: Mess Duri Sektor Timur"
            error={errors.mess_name?.message}
            {...register("mess_name")}
          />
          <TextField
            label="Kota / Wilayah"
            placeholder="Misal: Duri, Pekanbaru, Dumai"
            error={errors.city?.message}
            {...register("city")}
          />
        </div>

        <TextAreaField
          label="Alamat Lengkap Mess"
          placeholder="Jl. Hang Tuah No. 12, Kel. Air Jamban"
          rows={2}
          error={errors.address?.message}
          {...register("address")}
        />

        <div className="grid grid-cols-2 gap-2">
          <TextField
            label="Latitude"
            type="number"
            min={-90}
            max={90}
            step="any"
            placeholder="misal: 1.2845"
            error={errors.latitude?.message}
            {...register("latitude", { valueAsNumber: true })}
          />
          <TextField
            label="Longitude"
            type="number"
            min={-180}
            max={180}
            step="any"
            placeholder="misal: 101.218"
            error={errors.longitude?.message}
            {...register("longitude", { valueAsNumber: true })}
          />
        </div>

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
