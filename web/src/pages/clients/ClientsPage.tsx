import { useState } from "react";
import { ClientsTemplate } from "@/components/templates/clients/ClientsTemplate";
import { useClients, type Client } from "@/services/clientService";
import { useSession } from "@/stores/sessionStore";

export function ClientsPage() {
  const { me } = useSession();
  const canManage =
    Boolean(me?.permissions.includes("create:plan")) ||
    me?.role === "PROJECT_MANAGER" ||
    me?.role === "OPERATIONAL_MANAGER" ||
    me?.role === "SUPER_ADMIN";

  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Client | "new" | null>(null);
  const [removing, setRemoving] = useState<Client | null>(null);

  const clientsQuery = useClients(true, search || undefined);

  return (
    <ClientsTemplate
      clients={clientsQuery}
      canManage={canManage}
      editing={editing}
      removing={removing}
      search={search}
      onSearchChange={setSearch}
      onAdd={() => setEditing("new")}
      onEdit={setEditing}
      onDeactivate={setRemoving}
      onCloseEdit={() => setEditing(null)}
      onCloseRemove={() => setRemoving(null)}
    />
  );
}
