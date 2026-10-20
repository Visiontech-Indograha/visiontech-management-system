import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { errorMessage } from "@/lib/errors";
import { useDeleteAsset, useSetAssetStatus, type AssetKind, type ManualStatus } from "@/services/assetService";
import { AssetFormDialog } from "./AssetFormDialog";

const MANUAL: ManualStatus[] = ["ready", "damaged", "lost", "pension"];

/** Ubah status manual (siap/rusak/hilang/pensiun) atau hapus aset — ditolak API bila aset sedang dipinjam. */
export function AssetStatusDialog({ kind, id, name, status, onClose }: {
  kind: AssetKind;
  id: string;
  name: string;
  status: string;
  onClose: () => void;
}) {
  const setStatus = useSetAssetStatus();
  const remove = useDeleteAsset();
  const [value, setValue] = useState<ManualStatus>(MANUAL.includes(status as ManualStatus) ? (status as ManualStatus) : "ready");
  const [formError, setFormError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    try {
      await setStatus.mutateAsync({ kind, id, status: value });
      toast.success(`Status ${name} diperbarui.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };
  const onDelete = async () => {
    if (!window.confirm(`Hapus ${name} dari inventaris?`)) return;
    try {
      await remove.mutateAsync({ kind, id });
      toast.success(`${name} dihapus.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };

  return (
    <AssetFormDialog title={`Status ${name}`} submitting={setStatus.isPending} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Status" value={value} onChange={(e) => setValue(e.target.value as ManualStatus)}>
        <ControlOption value="ready">Siap dipakai</ControlOption>
        <ControlOption value="damaged">Rusak</ControlOption>
        <ControlOption value="lost">Hilang</ControlOption>
        <ControlOption value="pension">Pensiun (tidak dipakai lagi)</ControlOption>
      </SelectField>
      <ActionButton variant="outline" size="sm" onClick={onDelete} disabled={remove.isPending}>
        Hapus dari inventaris
      </ActionButton>
    </AssetFormDialog>
  );
}
