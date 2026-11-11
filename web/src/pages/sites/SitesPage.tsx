import { useState } from "react";
import { SitesTemplate } from "@/components/templates/sites/SitesTemplate";
import { useListControls } from "@/hooks/useListControls";
import { usePagedList } from "@/hooks/usePagedList";
import type { Site } from "@/services/siteService";

/** Master lokasi kerja (geofence absensi): GET/POST/DELETE /sites, izin manage:sites (R-33).
 * PM → lokasi proyek untuk bawahannya (unit ditetapkan server); Finance → lokasi kantor. */
export function SitesPage() {
  const controls = useListControls({ prefix: "lok_" });
  const sites = usePagedList<Site>(["sites"], "/offices", controls);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Site | null>(null);
  const [removing, setRemoving] = useState<Site | null>(null);

  return (
    <SitesTemplate
      controls={controls}
      sites={sites}
      adding={adding}
      editing={editing}
      removing={removing}
      onEdit={setEditing}
      onCloseEdit={() => setEditing(null)}
      onAdd={() => setAdding(true)}
      onRemove={setRemoving}
      onCloseAdd={() => setAdding(false)}
      onCloseRemove={() => setRemoving(null)}
    />
  );
}
