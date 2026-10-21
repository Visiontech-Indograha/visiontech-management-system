import type { FieldErrors, UseFormRegister } from "react-hook-form";
import { useWatch, type Control } from "react-hook-form";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import type { EmployeeFormValues } from "@/lib/employeeForm";
import { useDivisions, useJobPositions, useOffices } from "@/services/employeeService";

/** Isian data kerja: no., nama, kantor, divisi, jabatan (disaring per divisi), bergabung, akhir PKWT. */
export function EmployeeFormFields({ register, errors, control }: {
  register: UseFormRegister<EmployeeFormValues>;
  errors: FieldErrors<EmployeeFormValues>;
  control: Control<EmployeeFormValues>;
}) {
  const offices = useOffices();
  const divisions = useDivisions();
  const positions = useJobPositions();
  const divisionId = useWatch({ control, name: "division_id" });
  const positionOptions = (positions.data ?? []).filter(
    (p) => p.status && (!p.division_id || !divisionId || p.division_id === divisionId),
  );

  return (
    <>
      <TextField label="No. karyawan" error={errors.employee_no?.message} {...register("employee_no")} />
      <TextField label="Nama lengkap" error={errors.full_name?.message} {...register("full_name")} />
      <SelectField label="Kantor" error={errors.office_id?.message} {...register("office_id")}>
        <ControlOption value="" disabled>{offices.isPending ? "Memuat kantor..." : "Pilih kantor"}</ControlOption>
        {offices.data?.map((o) => <ControlOption key={o.id} value={o.id}>{o.name}</ControlOption>)}
      </SelectField>
      <SelectField label="Divisi" error={errors.division_id?.message} {...register("division_id")}>
        <ControlOption value="">Tanpa divisi</ControlOption>
        {divisions.data?.map((d) => <ControlOption key={d.id} value={d.id}>{d.name}</ControlOption>)}
      </SelectField>
      <SelectField label="Jabatan" error={errors.position_id?.message} {...register("position_id")}>
        <ControlOption value="">Tanpa jabatan</ControlOption>
        {positionOptions.map((p) => (
          <ControlOption key={p.position_id} value={p.position_id}>{`${p.name} (${p.code})`}</ControlOption>
        ))}
      </SelectField>
      <TextField label="Tanggal bergabung" type="date" error={errors.join_date?.message} {...register("join_date")} />
      <TextField
        label="Akhir PKWT"
        type="date"
        hint="Kosongkan untuk karyawan tetap"
        error={errors.pkwt_end_date?.message}
        {...register("pkwt_end_date")}
      />
      <TextBlock className="mb-2 text-caption text-mist">Akun login dibuat terpisah di kartu Akun pada halaman detail.</TextBlock>
    </>
  );
}
