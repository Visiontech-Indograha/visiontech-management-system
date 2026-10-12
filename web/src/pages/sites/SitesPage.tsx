import { useState } from "react";
import { SitesTemplate } from "@/components/templates/sites/SitesTemplate";
import { type Site, useSites } from "@/services/siteService";

/** Master lokasi kerja (geofence absensi): GET/POST/DELETE /sites, izin manage:sites (R-33).
 * PM → lokasi proyek untuk bawahannya (unit ditetapkan server); Finance → lokasi kantor. */
export function SitesPage() {
  const sites = useSites();
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<Site | null>(null);

  return (
    <SitesTemplate
      sites={sites}
      adding={adding}
      removing={removing}
      onAdd={() => setAdding(true)}
      onRemove={setRemoving}
      onCloseAdd={() => setAdding(false)}
      onCloseRemove={() => setRemoving(null)}
    />
  );
}
