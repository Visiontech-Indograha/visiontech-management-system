import { useState } from "react";
import { toast } from "sonner";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { errorMessage } from "@/lib/errors";
import { useReturnLoan, type Loan, type ReturnCondition } from "@/services/assetService";
import { AssetFormDialog } from "./AssetFormDialog";

/** Pengelola aset menerima pengembalian; kondisinya menjadi status aset (siap/rusak/hilang). */
export function AssetReturnDialog({ loan, onClose }: { loan: Loan; onClose: () => void }) {
  const giveBack = useReturnLoan();
  const [condition, setCondition] = useState<ReturnCondition>("ready");
  const [formError, setFormError] = useState<string | null>(null);
  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    try {
      await giveBack.mutateAsync({ assignmentId: loan.assignment_id, condition });
      toast.success(`${loan.asset_name} dikembalikan.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };
  return (
    <AssetFormDialog
      title={`Terima ${loan.asset_name} dari ${loan.employee_name}`}
      submitLabel="Terima pengembalian"
      submitting={giveBack.isPending}
      formError={formError}
      onClose={onClose}
      onSubmit={onSubmit}
    >
      <SelectField label="Kondisi saat dikembalikan" value={condition} onChange={(e) => setCondition(e.target.value as ReturnCondition)}>
        <ControlOption value="ready">Baik — siap dipakai lagi</ControlOption>
        <ControlOption value="damaged">Rusak</ControlOption>
        <ControlOption value="lost">Hilang</ControlOption>
      </SelectField>
    </AssetFormDialog>
  );
}
