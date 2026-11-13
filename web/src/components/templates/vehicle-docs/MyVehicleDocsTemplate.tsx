import { MyVehicleDocsPanel } from "@/components/organisms/vehicle-docs/MyVehicleDocsPanel";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Dokumen saya" (SIM dan sejenisnya) untuk karyawan. */
export function MyVehicleDocsTemplate() {
  return (
    <PageTemplate title="Dokumen saya" description="SIM dan dokumen lain atas nama Anda beserta tanggal jatuh temponya.">
      <MyVehicleDocsPanel />
    </PageTemplate>
  );
}
