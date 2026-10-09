import { useState } from "react";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { type Site, useSites } from "@/services/siteService";
import { SiteAddButton } from "@/components/organisms/sites/SiteAddButton";
import { SiteDeleteDialog } from "@/components/organisms/sites/SiteDeleteDialog";
import { SiteFormDialog } from "@/components/organisms/sites/SiteFormDialog";
import { SiteList } from "@/components/organisms/sites/SiteList";

/** Master lokasi kerja (geofence absensi): GET/POST/DELETE /sites, izin manage:sites (R-33).
 * PM → lokasi proyek untuk bawahannya (unit ditetapkan server); Finance → lokasi kantor. */
export function SitesPage() {
  const sites = useSites();
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<Site | null>(null);

  return (
    <PageTemplate title="Lokasi kerja" action={<SiteAddButton onAdd={() => setAdding(true)} />}>
      <SiteList sites={sites} onAdd={() => setAdding(true)} onRemove={setRemoving} />
      {adding && <SiteFormDialog onClose={() => setAdding(false)} />}
      {removing && <SiteDeleteDialog site={removing} onClose={() => setRemoving(null)} />}
    </PageTemplate>
  );
}
