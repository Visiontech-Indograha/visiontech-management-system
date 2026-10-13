import { SelectField } from "@/components/molecules/Field";
import { useActivePlans } from "@/services/assetService";
import { ControlOption } from "@/components/molecules/FormBlock";

/** Pilihan rencana kerja aktif untuk alokasi/pelepasan aset. */
export function AssetPlanSelect({ error, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { error?: string; ref?: React.Ref<HTMLSelectElement> }) {
  const plans = useActivePlans();
  return (
    <SelectField label="Work plan" error={error} hint={plans.isError ? "Daftar work plan tidak dapat dimuat." : undefined} {...props}>
      <ControlOption value="">{plans.isPending ? "Memuat..." : "Pilih work plan"}</ControlOption>
      {plans.data?.map((p) => (
        <ControlOption key={p.id} value={p.id}>
          {p.number ? `${p.number} · ` : ""}
          {p.title}
        </ControlOption>
      ))}
    </SelectField>
  );
}
