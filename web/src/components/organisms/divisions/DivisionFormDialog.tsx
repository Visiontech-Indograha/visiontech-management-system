import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { Notice, NoticeDescription } from "@/components/molecules/Notice";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { divisionSchema, type DivisionValues } from "@/schemas/divisionAdminSchemas";
import { useDivisionPeople, useSaveDivision, type DivisionRow } from "@/services/divisionAdminService";

const KNOWN = ["name", "om_id", "pm_id"] as const;

/** Dialog tambah/ubah divisi: nama, Operational Manager (OM), dan Project Manager (PM) dari karyawan yang sudah ada. */
export function DivisionFormDialog({ division, onClose }: { division: DivisionRow | null; onClose: () => void }) {
  const save = useSaveDivision(division?.id);
  const [formError, setFormError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const people = useDivisionPeople(useDebouncedValue(search.trim()));
  const {
    register,
    handleSubmit,
    control,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<DivisionValues>({
    resolver: zodResolver(divisionSchema),
    defaultValues: { name: division?.name ?? "", om_id: division?.om_id ?? "", pm_id: division?.pm_id ?? "" },
  });
  const omId = useWatch({ control, name: "om_id" });
  const pmId = useWatch({ control, name: "pm_id" });
  const list = people.data ?? [];
  const options = (current: string, currentName?: string | null) =>
    current && !list.some((p) => p.employee_id === current) ? (
      <ControlOption value={current}>{currentName || "Pilihan saat ini"}</ControlOption>
    ) : null;

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await save.mutateAsync({ name: v.name.trim(), om_id: v.om_id, pm_id: v.pm_id });
      toast.success(division ? "Divisi disimpan." : "Divisi ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(applyFieldErrors(err, setError, KNOWN) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  });

  return (
    <VmsDialog
      open
      dirty={isDirty}
      title={division ? "Ubah divisi" : "Tambah divisi"}
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={isSubmitting} formId="division-form" />}
    >
      <FormBlock id="division-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <Notice>
          <NoticeDescription>
            Atasan divisi dipilih dari karyawan yang sudah terdaftar. Bila orangnya belum ada, tambahkan dulu di menu Direktori.
          </NoticeDescription>
        </Notice>
        <TextField label="Nama divisi" maxLength={100} error={errors.name?.message} {...register("name")} />
        <TextField
          label="Cari karyawan"
          hint="Ketik awal nama untuk mempersempit pilihan di bawah."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <SelectField label="Operational Manager (OM)" error={errors.om_id?.message} {...register("om_id")}>
          <ControlOption value="">Pilih karyawan</ControlOption>
          {options(omId, division?.om_name)}
          {list.map((p) => (
            <ControlOption key={p.employee_id} value={p.employee_id}>{`${p.full_name} (${p.employee_no})`}</ControlOption>
          ))}
        </SelectField>
        <SelectField label="Project Manager (PM)" error={errors.pm_id?.message} {...register("pm_id")}>
          <ControlOption value="">Pilih karyawan</ControlOption>
          {options(pmId, division?.pm_name)}
          {list.map((p) => (
            <ControlOption key={p.employee_id} value={p.employee_id}>{`${p.full_name} (${p.employee_no})`}</ControlOption>
          ))}
        </SelectField>
      </FormBlock>
    </VmsDialog>
  );
}
