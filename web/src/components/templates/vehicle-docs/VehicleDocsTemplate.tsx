import { useState } from "react";
import { ExpiringDocsPanel } from "@/components/organisms/vehicle-docs/ExpiringDocsPanel";
import { VehicleDocumentDialog } from "@/components/organisms/vehicle-docs/VehicleDocumentDialog";
import type { VehicleDocument } from "@/services/vehicleDocumentService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Dokumen kendaraan": daftar yang akan jatuh tempo + dialog perbarui dokumen. */
export function VehicleDocsTemplate({ canManage }: { canManage: boolean }) {
  const [renewing, setRenewing] = useState<VehicleDocument | null>(null);
  return (
    <PageTemplate title="Dokumen kendaraan" description="STNK, KIR, pajak tahunan, dan dokumen lain yang akan atau sudah jatuh tempo.">
      <ExpiringDocsPanel canManage={canManage} onRenew={setRenewing} />
      {renewing && <VehicleDocumentDialog vehicleId={renewing.vehicle_id} plate={renewing.number_plate} docTypeCode={renewing.doc_type_code} onClose={() => setRenewing(null)} />}
    </PageTemplate>
  );
}
