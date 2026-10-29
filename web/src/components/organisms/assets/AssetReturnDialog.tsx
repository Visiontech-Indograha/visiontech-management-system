import { useState } from "react";
import { toast } from "sonner";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useFileUrl } from "@/hooks/useFileUrl";
import { errorMessage } from "@/lib/errors";
import { useReturnLoan, type Loan, type ReturnCondition } from "@/services/assetService";
import { AssetFormDialog } from "./AssetFormDialog";

/** Pengelola aset menerima pengembalian; kondisinya menjadi status aset (siap/rusak/hilang). */
export function AssetReturnDialog({ loan, onClose }: { loan: Loan; onClose: () => void }) {
  const giveBack = useReturnLoan();
  const { data: photoUrl } = useFileUrl(loan.return_file_id, "view");
  const [condition, setCondition] = useState<ReturnCondition>(loan.return_condition ?? "ready");
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
      {photoUrl && (
        <div className="aspect-[4/3] overflow-hidden rounded-control border border-line bg-hover">
          <ImageView src={photoUrl} alt="Foto kondisi dari karyawan" className="h-full w-full object-cover" />
        </div>
      )}
      {loan.return_note && <TextBlock className="text-sm text-mist">Catatan karyawan: {loan.return_note}</TextBlock>}
      <SelectField label="Kondisi saat dikembalikan" value={condition} onChange={(e) => setCondition(e.target.value as ReturnCondition)}>
        <ControlOption value="ready">Baik — siap dipakai lagi</ControlOption>
        <ControlOption value="damaged">Rusak</ControlOption>
        <ControlOption value="lost">Hilang</ControlOption>
      </SelectField>
    </AssetFormDialog>
  );
}
