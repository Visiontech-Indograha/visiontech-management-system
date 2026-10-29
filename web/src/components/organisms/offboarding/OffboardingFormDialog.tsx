import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { useDirtyForm } from "@/hooks/useDirtyForm";
import { errorMessage } from "@/lib/errors";
import { useEmployees } from "@/services/employeeService";
import { REASON_LABEL, useCreateOffboarding, type OffboardingCreate } from "@/services/offboardingService";

/**
 * HR memulai offboarding (docs/35 §7). Karyawan bisa ditetapkan dari luar (detail karyawan / daftar PKWT).
 * Tanggal efektif kosong + PKWT berakhir → server memakai tanggal akhir PKWT.
 */
export function OffboardingFormDialog({ employee, onClose }: {
  employee?: { id: string; name: string };
  onClose: () => void;
}) {
  const create = useCreateOffboarding();
  const employees = useEmployees({ status: "active", page: 1, size: 100 });
  const [employeeId, setEmployeeId] = useState(employee?.id ?? "");
  const [reason, setReason] = useState<OffboardingCreate["reason_type"]>("PKWT_EXPIRED");
  const [effective, setEffective] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!employeeId) return setError("Pilih karyawan.");
    if (!effective && reason !== "PKWT_EXPIRED") return setError("Isi tanggal efektif.");
    try {
      const created = await create.mutateAsync({
        employee_id: employeeId,
        reason_type: reason,
        effective_date: effective || null,
        notes: notes.trim() || null,
      });
      const pending = created.clearance_items?.length ?? 0;
      toast.success(pending ? `Offboarding dimulai: ${pending} barang harus dikembalikan.` : "Offboarding dimulai.");
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const dirtyForm = useDirtyForm();
  return (
    <VmsDialog dirty={dirtyForm.dirty}
      open
      title={employee ? `Offboarding ${employee.name}` : "Mulai offboarding"}
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={create.isPending}>Batal</ActionButton>
          <ActionButton type="submit" form="offboarding-form" variant="destructive" disabled={create.isPending}>
            {create.isPending ? "Memproses..." : "Mulai offboarding"}
          </ActionButton>
        </>
      }
    >
      <FormBlock {...dirtyForm.formProps} id="offboarding-form" onSubmit={submit} noValidate className="space-y-3">
        <FormErrorText message={error} />
        <TextBlock className="text-sm text-mist">
          Pinjaman alat & kendaraan yang belum kembali otomatis masuk daftar clearance. Akun baru dinonaktifkan setelah
          barang lengkap, PM & HR menyetujui, dan tanggal efektif tiba.
        </TextBlock>
        {!employee && (
          <SelectField label="Karyawan" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
            <ControlOption value="">Pilih karyawan…</ControlOption>
            {(employees.data?.items ?? []).map((e) => (
              <ControlOption key={e.employee_id} value={e.employee_id}>{`${e.full_name} (${e.employee_no})`}</ControlOption>
            ))}
          </SelectField>
        )}
        <SelectField label="Alasan" value={reason}
                     onChange={(e) => setReason(e.target.value as OffboardingCreate["reason_type"])}>
          {Object.entries(REASON_LABEL).map(([v, l]) => <ControlOption key={v} value={v}>{l}</ControlOption>)}
        </SelectField>
        <TextField label="Tanggal efektif" type="date" value={effective} onChange={(e) => setEffective(e.target.value)}
                   hint={reason === "PKWT_EXPIRED" ? "Kosongkan untuk memakai tanggal akhir PKWT." : undefined} />
        <TextAreaField label="Catatan" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </FormBlock>
    </VmsDialog>
  );
}
