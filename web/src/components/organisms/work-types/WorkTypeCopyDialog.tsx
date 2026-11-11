import { divisionOptionLabel } from "@/lib/divisionLabel";
import { useState } from "react";
import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { useDivisions } from "@/services/employeeService";
import { useCopyWorkTypeToDivision, type WorkType } from "@/services/workTypeService";

/** Salin jenis pekerjaan (slot foto + BoM standar) ke divisi lain sebagai jenis baru di divisi itu. */
export function WorkTypeCopyDialog({ type, onClose }: { type: WorkType; onClose: () => void }) {
  const { data: divisions = [] } = useDivisions();
  const copy = useCopyWorkTypeToDivision();
  const [target, setTarget] = useState("");
  const targets = divisions.filter((d) => d.id !== type.division_id);
  const confirm = async () => {
    if (!target) {
      toast.error("Pilih divisi tujuan.");
      return;
    }
    try {
      await copy.mutateAsync({ id: type.id, division_id: target });
      toast.success("Jenis pekerjaan disalin ke divisi tujuan.");
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <VmsDialog
      open
      title="Salin ke divisi"
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={copy.isPending}>
            Batal
          </ActionButton>
          <ActionButton onClick={confirm} disabled={copy.isPending || !target}>
            Salin
          </ActionButton>
        </>
      }
    >
      <TextBlock className="mb-3 text-sm">
        <TextBlock as="strong" className="text-ink">{type.name}</TextBlock> disalin beserta slot foto dan BoM standar.
        Divisi tujuan mendapat jenis pekerjaan sendiri yang bisa diubah terpisah.
      </TextBlock>
      <SelectField label="Divisi tujuan" value={target} onChange={(e) => setTarget(e.target.value)}>
        <ControlOption value="">Pilih divisi</ControlOption>
        {targets.map((d) => (
          <ControlOption key={d.id} value={d.id}>
            {divisionOptionLabel(d, targets)}
          </ControlOption>
        ))}
      </SelectField>
    </VmsDialog>
  );
}
