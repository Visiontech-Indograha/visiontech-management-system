import { BandingPanel } from "@/components/organisms/hikvision/BandingPanel";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Banding mesin": absen dari mesin dibandingkan dengan absen di aplikasi. */
export function HikvisionBandingTemplate() {
  return (
    <PageTemplate
      title="Banding mesin"
      description="Bandingkan catatan mesin absensi dengan absen di aplikasi (HP atau web). Halaman ini hanya untuk dilihat, tidak mengubah absen."
    >
      <BandingPanel />
    </PageTemplate>
  );
}
