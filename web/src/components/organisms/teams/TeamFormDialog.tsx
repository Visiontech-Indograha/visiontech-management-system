import { useState } from "react";
import { toast } from "sonner";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { useDirtyForm } from "@/hooks/useDirtyForm";
import { errorMessage } from "@/lib/errors";
import { useEmployees, useOffices, useUserDivisions } from "@/services/employeeService";
import { useCreateTeam } from "@/services/teamService";

/** Tambah tim lapangan: nama, divisi, kantor, ketua (pilih karyawan — bukan ketik ID). Anggota ditambah lewat Detail. */
export function TeamFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateTeam();
  const divisions = useUserDivisions();
  const offices = useOffices();
  const [q, setQ] = useState("");
  const employees = useEmployees({ status: "active", page: 1, q: q.trim() || undefined });
  const [name, setName] = useState("");
  const [divisionId, setDivisionId] = useState("");
  const [officeId, setOfficeId] = useState("");
  const [leaderId, setLeaderId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const effectiveDivisionId = divisionId || (divisions.data?.length === 1 ? divisions.data[0].id : "");

  const submit = async () => {
    setError(null);
    if (name.trim().length < 2 || !effectiveDivisionId || !officeId || !leaderId)
      return setError("Isi nama tim, divisi, kantor, dan ketua tim.");
    try {
      await create.mutateAsync({ name: name.trim(), division_id: effectiveDivisionId, office_id: officeId, leader_employee_id: leaderId, status: true });
      toast.success("Tim ditambahkan. Tambah anggotanya lewat tombol Anggota & kontak.");
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const dirtyForm = useDirtyForm();
  return (
    <VmsDialog dirty={dirtyForm.dirty}
      open
      title="Tambah tim lapangan"
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={create.isPending} formId="team-form" />}
    >
      <FormBlock {...dirtyForm.formProps}
        id="team-form"
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <FormErrorText message={error} />
        <TextField label="Nama tim" value={name} onChange={(e) => setName(e.target.value)} placeholder="mis. Tim CCTV Pekanbaru 2" />
        <SelectField label="Divisi" value={effectiveDivisionId} onChange={(e) => setDivisionId(e.target.value)}>
          <ControlOption value="">Pilih divisi</ControlOption>
          {(divisions.data ?? []).map((d) => (
            <ControlOption key={d.id} value={d.id}>{d.name}</ControlOption>
          ))}
        </SelectField>
        <SelectField label="Kantor" value={officeId} onChange={(e) => setOfficeId(e.target.value)}>
          <ControlOption value="">Pilih kantor</ControlOption>
          {(offices.data ?? []).map((o) => (
            <ControlOption key={o.id} value={o.id}>{o.name}</ControlOption>
          ))}
        </SelectField>
        <TextField label="Cari calon ketua" placeholder="Nama / NIK" value={q} onChange={(e) => setQ(e.target.value)} />
        <SelectField label="Ketua tim" value={leaderId} onChange={(e) => setLeaderId(e.target.value)}>
          <ControlOption value="">Pilih ketua tim</ControlOption>
          {(employees.data?.items ?? []).map((e) => (
            <ControlOption key={e.employee_id} value={e.employee_id}>{`${e.full_name} (${e.employee_no})`}</ControlOption>
          ))}
        </SelectField>
      </FormBlock>
    </VmsDialog>
  );
}
