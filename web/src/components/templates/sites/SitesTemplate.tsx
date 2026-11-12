import type { UseQueryResult } from "@tanstack/react-query";
import { SiteAddButton } from "@/components/organisms/sites/SiteAddButton";
import { SiteDeleteDialog } from "@/components/organisms/sites/SiteDeleteDialog";
import { SiteFormDialog } from "@/components/organisms/sites/SiteFormDialog";
import { SiteList } from "@/components/organisms/sites/SiteList";
import type { ListControls } from "@/hooks/usePagedList";
import type { Paged } from "@/lib/paged";
import type { Site } from "@/services/siteService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Lokasi kerja": daftar lokasi + dialog tambah/hapus. */
export function SitesTemplate({ controls, sites, adding, editing, removing, onAdd, onEdit, onRemove, onCloseEdit, onCloseAdd, onCloseRemove }: {
  controls: ListControls;
  sites: UseQueryResult<Paged<Site>>;
  adding: boolean;
  editing: Site | null;
  removing: Site | null;
  onAdd: () => void;
  onEdit: (site: Site) => void;
  onCloseEdit: () => void;
  onRemove: (site: Site) => void;
  onCloseAdd: () => void;
  onCloseRemove: () => void;
}) {
  return (
    <PageTemplate title="Lokasi kerja" action={<SiteAddButton onAdd={onAdd} />}>
      <SiteList controls={controls} sites={sites} onAdd={onAdd} onRemove={onRemove} onEdit={onEdit} />
      {adding && <SiteFormDialog onClose={onCloseAdd} />}
      {editing && <SiteFormDialog site={editing} onClose={onCloseEdit} />}
      {removing && <SiteDeleteDialog site={removing} onClose={onCloseRemove} />}
    </PageTemplate>
  );
}
