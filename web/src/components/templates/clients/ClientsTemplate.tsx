import type { UseQueryResult } from "@tanstack/react-query";
import { WorkCompletionNavTabs } from "@/components/organisms/work-completions/WorkCompletionNavTabs";
import { ClientAddButton } from "@/components/organisms/clients/ClientAddButton";
import { ClientFormDialog } from "@/components/organisms/clients/ClientFormDialog";
import { ClientDeactivateDialog } from "@/components/organisms/clients/ClientDeactivateDialog";
import { ClientSitesModal } from "@/components/organisms/clients/ClientSitesModal";
import { ClientList } from "@/components/organisms/clients/ClientList";
import type { Client } from "@/services/clientService";
import { PageTemplate } from "../PageTemplate";

export function ClientsTemplate({
  clients,
  canManage,
  editing,
  removing,
  managingSites,
  search,
  onSearchChange,
  onAdd,
  onEdit,
  onDeactivate,
  onManageSites,
  onCloseEdit,
  onCloseRemove,
  onCloseManageSites,
  onUseExisting,
}: {
  clients: UseQueryResult<Client[]>;
  canManage: boolean;
  editing: Client | "new" | null;
  removing: Client | null;
  managingSites: Client | null;
  search: string;
  onSearchChange: (value: string) => void;
  onAdd: () => void;
  onEdit: (client: Client) => void;
  onDeactivate: (client: Client) => void;
  onManageSites: (client: Client) => void;
  onCloseEdit: () => void;
  onCloseRemove: () => void;
  onCloseManageSites: () => void;
  onUseExisting: (clientId: string) => void;
}) {
  return (
    <PageTemplate
      title="Master Klien"
      description="Kelola daftar perusahaan klien, narahubung (PIC), dan riwayat keterlibatan proyek."
      action={canManage && <ClientAddButton onAdd={onAdd} />}
    >
      <WorkCompletionNavTabs activeTab="clients" />
      <ClientList
        clients={clients}
        canManage={canManage}
        onAdd={onAdd}
        onEdit={onEdit}
        onDeactivate={onDeactivate}
        onManageSites={onManageSites}
        search={search}
        onSearchChange={onSearchChange}
      />
      {editing && (
        <ClientFormDialog
          key={editing === "new" ? "new" : editing.client_id}
          client={editing === "new" ? null : editing}
          onClose={onCloseEdit}
          onUseExisting={onUseExisting}
        />
      )}
      {removing && (
        <ClientDeactivateDialog client={removing} onClose={onCloseRemove} />
      )}
      {managingSites && (
        <ClientSitesModal client={managingSites} onClose={onCloseManageSites} />
      )}
    </PageTemplate>
  );
}
