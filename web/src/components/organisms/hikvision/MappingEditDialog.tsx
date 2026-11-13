import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { mappingSchema, type MappingValues } from "@/schemas/hikvisionSchemas";
import { useEmployees } from "@/services/employeeService";
import { useSaveMapping, type Pemetaan } from "@/services/hikvisionService";

type Row = { employee_id: string; full_name: string; employee_no: string };

function EmployeeOptions({ rows, pending, current }: { rows: Row[]; pending: boolean; current?: Pemetaan }) {
  const missing = current && !rows.some((r) => r.employee_id === current.employee_id);
  let first = "Pilih karyawan";
  if (pending) first = "Memuat...";
  else if (rows.length === 0 && !current) first = "Karyawan tidak ditemukan";
  return (
    <>
      <ControlOption value="">{first}</ControlOption>
      {missing && <ControlOption value={current.employee_id}>{current.full_name} ({current.employee_no})</ControlOption>}
      {rows.map((r) => (
        <ControlOption key={r.employee_id} value={r.employee_id}>{r.full_name} ({r.employee_no})</ControlOption>
      ))}
    </>
  );
}

/** Tambah/ubah satu pemetaan: nomor di mesin -> karyawan. Nomor di mesin tidak bisa diubah setelah dibuat. */
export function MappingEditDialog({ deviceId, mapping, onClose }: { deviceId: string; mapping?: Pemetaan; onClose: () => void }) {
  const save = useSaveMapping(deviceId);
  const [formError, setFormError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const q = useDebouncedValue(search.trim());
  const employees = useEmployees({ status: "active", page: 1, size: 20, q: q || undefined });
  const { register, handleSubmit, setError, formState: { errors, isSubmitting, isDirty } } = useForm<MappingValues>({
    resolver: zodResolver(mappingSchema),
    defaultValues: { employee_no_string: mapping?.employee_no_string ?? "", employee_id: mapping?.employee_id ?? "" },
  });
  const rows = employees.data?.items ?? [];

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await save.mutateAsync({ mapId: mapping?.map_id, ...v });
      toast.success(mapping ? "Pemetaan diubah." : "Pemetaan ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(applyFieldErrors(err, setError, ["employee_no_string", "employee_id"]) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  });

  return (
    <VmsDialog
      dirty={isDirty}
      open
      title={mapping ? "Ubah pemetaan" : "Tambah pemetaan"}
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={isSubmitting} formId="hik-map-form" />}
    >
      <FormBlock id="hik-map-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <TextField label="Nomor karyawan di mesin" maxLength={50} disabled={!!mapping} error={errors.employee_no_string?.message} {...register("employee_no_string")} />
        <TextField label="Cari karyawan" maxLength={100} hint="Ketik nama atau nomor karyawan, lalu pilih di bawah." value={search} onChange={(e) => setSearch(e.target.value)} />
        <SelectField label="Karyawan" error={errors.employee_id?.message} {...register("employee_id")}>
          <EmployeeOptions rows={rows} pending={employees.isPending} current={mapping} />
        </SelectField>
      </FormBlock>
    </VmsDialog>
  );
}
