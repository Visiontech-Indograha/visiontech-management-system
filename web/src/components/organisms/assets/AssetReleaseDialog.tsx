import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { errorMessage } from "@/lib/errors";
import { releaseSchema } from "@/schemas/assetSchemas";
import { useReleaseAsset, type Asset } from "@/services/assetService";
import { AssetFormDialog } from "./AssetFormDialog";
import { AssetPlanSelect } from "./AssetPlanSelect";

/** Dialog lepas reservasi aset dari rencana kerja. */
export function AssetReleaseDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const release = useReleaseAsset();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ work_plan_id: string }>({ resolver: zodResolver(releaseSchema), defaultValues: { work_plan_id: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await release.mutateAsync({ id: asset.id, work_plan_id: v.work_plan_id });
      toast.success("Reservasi dilepas.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AssetFormDialog title={`Lepas reservasi ${asset.name}`} submitLabel="Lepas reservasi" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <p className="mb-3 text-sm text-mist">Pilih work plan yang memesan aset ini.</p>
      <AssetPlanSelect error={errors.work_plan_id?.message} {...register("work_plan_id")} />
    </AssetFormDialog>
  );
}
