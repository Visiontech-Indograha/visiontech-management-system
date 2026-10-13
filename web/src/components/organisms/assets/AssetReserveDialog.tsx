import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { SelectField } from "@/components/molecules/Field";
import { errorMessage } from "@/lib/errors";
import { useReserveAsset, type Asset } from "@/services/assetService";
import { useActiveEmployees } from "@/services/workPlanService";
import { AssetFormDialog } from "./AssetFormDialog";
import { AssetPlanSelect } from "./AssetPlanSelect";
import { ControlOption } from "@/components/molecules/FormBlock";

/** Dialog alokasi aset ke rencana kerja (+ pengemudi untuk kendaraan). */
export function AssetReserveDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const reserve = useReserveAsset();
  const employees = useActiveEmployees();
  const vehicle = asset.kind === "VEHICLE";
  const schema = z
    .object({ work_plan_id: z.string().min(1, "Pilih work plan."), driver_employee_id: z.string() })
    .refine((v) => !vehicle || v.driver_employee_id.length > 0, { path: ["driver_employee_id"], message: "Pilih pengemudi untuk aset kendaraan." });
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { work_plan_id: "", driver_employee_id: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await reserve.mutateAsync({ id: asset.id, work_plan_id: v.work_plan_id, driver_employee_id: vehicle ? v.driver_employee_id : null });
      toast.success("Aset dialokasikan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AssetFormDialog title={`Alokasikan ${asset.name}`} submitLabel="Alokasikan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <AssetPlanSelect error={errors.work_plan_id?.message} {...register("work_plan_id")} />
      {vehicle && (
        <SelectField label="Pengemudi" hint="Harus anggota tim penugasan." error={errors.driver_employee_id?.message} {...register("driver_employee_id")}>
          <ControlOption value="">{employees.isPending ? "Memuat..." : "Pilih pengemudi"}</ControlOption>
          {employees.data?.map((e) => (
            <ControlOption key={e.id} value={e.id}>
              {e.full_name}
            </ControlOption>
          ))}
        </SelectField>
      )}
    </AssetFormDialog>
  );
}
