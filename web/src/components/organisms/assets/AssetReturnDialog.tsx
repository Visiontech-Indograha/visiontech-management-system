import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { TextAreaField, TextField } from "@/components/molecules/Field";
import { errorMessage } from "@/lib/errors";
import { returnSchema, type ReturnValues } from "@/schemas/assetSchemas";
import { useRequestReturn, type Asset } from "@/services/assetService";
import { AssetFormDialog } from "./AssetFormDialog";

/** Ketua SK peminjam mengajukan pengembalian (BAST) — petugas aset memeriksanya. */
export function AssetReturnDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const requestReturn = useRequestReturn();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReturnValues>({ resolver: zodResolver(returnSchema), defaultValues: { condition_on_return: asset.condition, note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await requestReturn.mutateAsync({ allocation_id: asset.allocation_id!, condition_on_return: v.condition_on_return, note: v.note || null });
      toast.success("Pengembalian diajukan. Petugas aset akan memeriksa kondisinya.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AssetFormDialog title={`Kembalikan ${asset.name}`} submitLabel="Ajukan pengembalian" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Kondisi saat dikembalikan" error={errors.condition_on_return?.message} {...register("condition_on_return")} />
      <TextAreaField label="Catatan (opsional)" {...register("note")} />
    </AssetFormDialog>
  );
}
