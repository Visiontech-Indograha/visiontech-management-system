import { useState } from "react";
import { toast } from "sonner";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { useLend, type AssetKind } from "@/services/assetService";
import { useEmployees, useUploadFile } from "@/services/employeeService";
import { AssetFormDialog } from "./AssetFormDialog";

/** Serah terima aset ke karyawan + foto bukti (opsional). Aturan STNK/KIR/SIM & jadwal dijaga API. */
export function AssetLendDialog({ kind, assetId, assetName, onClose }: {
  kind: AssetKind;
  assetId: string;
  assetName: string;
  onClose: () => void;
}) {
  const lend = useLend();
  const upload = useUploadFile();
  const [q, setQ] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const employees = useEmployees({ q, status: "active", page: 1 });
  const [formError, setFormError] = useState<string | null>(null);
  const busy = lend.isPending || upload.isPending;

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    if (!employeeId) return setFormError("Pilih karyawan penerima.");
    const photo = (e.currentTarget.elements.namedItem("handover_photo") as HTMLInputElement | null)?.files?.[0];
    try {
      let handover_file_id: string | null = null;
      if (photo) {
        const body = new FormData();
        body.set("file", photo);
        handover_file_id = (await upload.mutateAsync(body)).file_id;
      }
      await lend.mutateAsync({
        asset_type: kind,
        ...(kind === "TOOL" ? { tool_id: assetId } : { vehicle_id: assetId }),
        employee_id: employeeId,
        handover_file_id,
      });
      toast.success(`${assetName} diserahkan.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };

  return (
    <AssetFormDialog title={`Serahkan ${assetName}`} submitLabel="Serahkan" submitting={busy} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      {kind === "VEHICLE" && (
        <TextBlock className="mb-3 text-sm text-mist">STNK harus berlaku (KIR untuk truk) dan pemegang wajib punya SIM yang sesuai.</TextBlock>
      )}
      <TextField label="Cari karyawan" value={q} onChange={(e) => setQ(e.target.value)} hint="Nama, NIK, atau email" />
      <SelectField label="Karyawan penerima" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
        <ControlOption value="">Pilih karyawan</ControlOption>
        {employees.data?.items.map((emp) => (
          <ControlOption key={emp.id} value={emp.id}>
            {emp.full_name} · {emp.employee_no}
          </ControlOption>
        ))}
      </SelectField>
      <TextField name="handover_photo" label="Foto serah terima (opsional)" type="file" accept=".jpg,.jpeg,.png" />
    </AssetFormDialog>
  );
}
