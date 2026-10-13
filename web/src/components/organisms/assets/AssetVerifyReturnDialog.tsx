import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { SelectField, TextAreaField } from "@/components/molecules/Field";
import { errorMessage } from "@/lib/errors";
import { verifySchema, type VerifyValues } from "@/schemas/assetSchemas";
import { useVerifyReturn, type Asset } from "@/services/assetService";
import { AssetFormDialog } from "./AssetFormDialog";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ControlOption } from "@/components/molecules/FormBlock";

/** Petugas aset: terima → aset tersedia lagi; tolak → kembali ke tim untuk diperbaiki (R9, tanpa jalan buntu). */
export function AssetVerifyReturnDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const verify = useVerifyReturn();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<VerifyValues>({ resolver: zodResolver(verifySchema), defaultValues: { decision: "ACCEPT", note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await verify.mutateAsync({ return_id: asset.pending_return_id!, is_accepted: v.decision === "ACCEPT", note: v.note || null });
      toast.success(v.decision === "ACCEPT" ? "Pengembalian diterima. Aset tersedia lagi." : "Pengembalian ditolak. Aset kembali ke tim.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AssetFormDialog title={`Periksa pengembalian ${asset.name}`} submitLabel="Simpan hasil" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextBlock className="mb-3 text-sm text-mist">
        Diajukan {asset.return_requested_by_name ?? "ketua tim"} · kondisi {asset.return_condition}
        {asset.return_note ? ` — ${asset.return_note}` : ""}
      </TextBlock>
      <SelectField label="Hasil pemeriksaan" {...register("decision")}>
        <ControlOption value="ACCEPT">Terima — aset tersedia lagi</ControlOption>
        <ControlOption value="REJECT">Tolak — kembali ke tim untuk diperbaiki</ControlOption>
      </SelectField>
      <TextAreaField label="Catatan (wajib jika ditolak)" error={errors.note?.message} {...register("note")} />
    </AssetFormDialog>
  );
}
