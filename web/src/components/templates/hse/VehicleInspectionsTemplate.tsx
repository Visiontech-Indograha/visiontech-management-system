import { VehicleInspectionsPanel } from "@/components/organisms/hse/VehicleInspectionsPanel";
import { PageTemplate } from "@/components/templates/PageTemplate";

export function VehicleInspectionsTemplate() {
  return (
    <VehicleInspectionsPanel
      renderPage={({ action, body }) => (
        <PageTemplate title="Inspeksi kendaraan" description="Periksa kondisi kendaraan, kirim foto bukti, dan lihat hasil pemeriksaan HSE." action={action}>
          {body}
        </PageTemplate>
      )}
    />
  );
}
