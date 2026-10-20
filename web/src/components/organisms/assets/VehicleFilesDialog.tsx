import { useState } from "react";
import { toast } from "sonner";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { FilePreview } from "@/components/molecules/FilePreview";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { useAddVehicleFile, useVehicleFiles, type Vehicle, type VehicleFile } from "@/services/assetService";
import { useUploadFile } from "@/services/employeeService";
import { AssetFormDialog } from "./AssetFormDialog";

const DOC_STATUS: Record<VehicleFile["status"], string> = { active: "ACTIVE", extended: "SUPERSEDED", not_active: "INACTIVE" };
type FileType = VehicleFile["type"];

/** Berkas kendaraan (STNK/BPKB/KIR): daftar + catat berkas baru (yang sejenis lama → diganti). */
export function VehicleFilesDialog({ vehicle, canManage, onClose }: { vehicle: Vehicle; canManage: boolean; onClose: () => void }) {
  const files = useVehicleFiles(vehicle.vehicle_id);
  const add = useAddVehicleFile(vehicle.vehicle_id);
  const upload = useUploadFile();
  const [type, setType] = useState<FileType>("STNK");
  const [formError, setFormError] = useState<string | null>(null);
  const busy = add.isPending || upload.isPending;

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!canManage) return onClose();
    setFormError(null);
    const form = e.currentTarget;
    const expired_at = String(new FormData(form).get("expired_at") ?? "");
    const file = (form.elements.namedItem("file") as HTMLInputElement | null)?.files?.[0];
    if (!expired_at) return setFormError("Tanggal berlaku sampai wajib diisi.");
    if (!file) return setFormError("File berkas wajib dilampirkan.");
    try {
      const body = new FormData();
      body.set("file", file);
      const { file_id } = await upload.mutateAsync(body);
      await add.mutateAsync({ type, file_id, expired_at });
      toast.success(`${type} dicatat.`);
      form.reset();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };

  return (
    <AssetFormDialog
      title={`Berkas ${vehicle.number_plate}`}
      submitLabel={canManage ? "Catat berkas" : "Tutup"}
      submitting={busy}
      formError={formError}
      onClose={onClose}
      onSubmit={onSubmit}
    >
      <ListBlock className="mb-4 divide-y divide-line">
        {files.data?.length === 0 && (
          <ListEntry>
            <TextBlock className="py-2 text-sm text-mist">Belum ada berkas.</TextBlock>
          </ListEntry>
        )}
        {files.data?.map((f) => (
          <ListEntry key={f.vehicle_file_id} className="flex items-center justify-between gap-3 py-2 text-sm">
            <TextBlock as="span" className="font-medium">{f.type}</TextBlock>
            <TextBlock as="span" className="text-mist">s.d. {formatDate(f.expired_at)}</TextBlock>
            <StatusBadge status={DOC_STATUS[f.status]} />
            {f.file_id && <FilePreview fileId={f.file_id} fileName={f.type} />}
          </ListEntry>
        ))}
      </ListBlock>
      {canManage && (
        <>
          <SelectField label="Jenis berkas" value={type} onChange={(e) => setType(e.target.value as FileType)}>
            <ControlOption value="STNK">STNK</ControlOption>
            <ControlOption value="KIR">KIR</ControlOption>
            <ControlOption value="BPKB">BPKB</ControlOption>
          </SelectField>
          <TextField name="expired_at" label="Berlaku sampai" type="date" />
          <TextField name="file" label="File (jpg, png, pdf)" type="file" accept=".jpg,.jpeg,.png,.pdf" />
        </>
      )}
    </AssetFormDialog>
  );
}
