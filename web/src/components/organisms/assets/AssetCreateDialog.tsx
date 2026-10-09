import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { SelectField, TextField } from "@/components/molecules/Field";
import { errorMessage } from "@/lib/errors";
import { createSchema, type CreateValues } from "@/schemas/assetSchemas";
import { useCreateAsset } from "@/services/assetService";
import { AssetFormDialog } from "./AssetFormDialog";
import { ControlOption } from "@/components/molecules/FormBlock";

/** Dialog "Tambah aset" (kendaraan atau alat). */
export function AssetCreateDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateAsset();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { kind: "VEHICLE", vehicle_type: "", code: "", name: "", condition: "Baik" },
  });
  const kind = useWatch({ control, name: "kind" });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await create.mutateAsync({ ...v, vehicle_type: v.kind === "VEHICLE" ? v.vehicle_type : null });
      toast.success("Aset ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AssetFormDialog title="Tambah aset" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Jenis aset" {...register("kind")}>
        <ControlOption value="VEHICLE">Kendaraan</ControlOption>
        <ControlOption value="TOOL">Peralatan</ControlOption>
      </SelectField>
      {kind === "VEHICLE" && <TextField label="Jenis kendaraan" hint="Contoh: Pick-up, Minibus" error={errors.vehicle_type?.message} {...register("vehicle_type")} />}
      <TextField label="Kode aset" error={errors.code?.message} {...register("code")} />
      <TextField label="Nama aset" error={errors.name?.message} {...register("name")} />
      <TextField label="Kondisi" error={errors.condition?.message} {...register("condition")} />
    </AssetFormDialog>
  );
}
