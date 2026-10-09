import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { SelectField, TextAreaField } from "@/components/molecules/Field";
import { errorMessage } from "@/lib/errors";
import { checkSchema, type CheckValues } from "@/schemas/assetSchemas";
import { useCheckAsset, type Asset } from "@/services/assetService";
import { AssetFormDialog } from "./AssetFormDialog";

/** Pengemudi yang ditunjuk menyatakan kendaraan layak (ACCEPT) atau banding (APPEAL). */
export function AssetCheckDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const check = useCheckAsset();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CheckValues>({ resolver: zodResolver(checkSchema), defaultValues: { decision: "ACCEPT", reason: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await check.mutateAsync({ id: asset.id, decision: v.decision, reason: v.reason || null });
      toast.success(v.decision === "ACCEPT" ? "Kendaraan dinyatakan layak." : "Banding kelayakan dikirim.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AssetFormDialog title="Periksa Kendaraan" submitLabel="Simpan hasil" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Hasil pemeriksaan" {...register("decision")}>
        <option value="ACCEPT">Kendaraan layak dipakai</option>
        <option value="APPEAL">Ajukan banding kelayakan</option>
      </SelectField>
      <TextAreaField label="Alasan (wajib jika banding)" error={errors.reason?.message} {...register("reason")} />
    </AssetFormDialog>
  );
}
