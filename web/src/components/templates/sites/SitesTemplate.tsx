import type { UseQueryResult } from "@tanstack/react-query";
import { SiteAddButton } from "@/components/organisms/sites/SiteAddButton";
import { SiteDeleteDialog } from "@/components/organisms/sites/SiteDeleteDialog";
import { SiteFormDialog } from "@/components/organisms/sites/SiteFormDialog";
import { SiteList } from "@/components/organisms/sites/SiteList";
import type { Site } from "@/services/siteService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Lokasi kerja": daftar lokasi + dialog tambah/hapus. */
export function SitesTemplate({ sites, adding, removing, onAdd, onRemove, onCloseAdd, onCloseRemove }: {
  sites: UseQueryResult<Site[]>;
  adding: boolean;
  removing: Site | null;
  onAdd: () => void;
  onRemove: (site: Site) => void;
  onCloseAdd: () => void;
  onCloseRemove: () => void;
}) {
  return (
    <PageTemplate title="Lokasi kerja" action={<SiteAddButton onAdd={onAdd} />}>
      <SiteList sites={sites} onAdd={onAdd} onRemove={onRemove} />
      {adding && <SiteFormDialog onClose={onCloseAdd} />}
      {removing && <SiteDeleteDialog site={removing} onClose={onCloseRemove} />}
    </PageTemplate>
  );
}
