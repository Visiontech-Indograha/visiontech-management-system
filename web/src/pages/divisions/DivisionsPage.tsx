import { useState } from "react";
import { DivisionsTemplate } from "@/components/templates/divisions/DivisionsTemplate";
import { useDivisionRows, usePositionRows, type DivisionDialog, type RemoveTarget } from "@/services/divisionAdminService";
import { useSession } from "@/stores/sessionStore";

/** Divisi dan jabatan: divisi butuh izin manage:divisions (OM, Super Admin); jabatan butuh manage:users (HR, Super Admin). */
export function DivisionsPage() {
  const permissions = useSession().me?.permissions ?? [];
  const divisions = useDivisionRows();
  const positions = usePositionRows();
  const [search, setSearch] = useState("");
  const [dialog, setDialog] = useState<DivisionDialog | null>(null);
  const [removing, setRemoving] = useState<RemoveTarget | null>(null);

  return (
    <DivisionsTemplate
      list={{
        divisions,
        positions,
        search,
        onSearch: setSearch,
        canDivisions: permissions.includes("manage:divisions"),
        canPositions: permissions.includes("manage:users"),
        onAddDivision: () => setDialog({ kind: "division", item: null }),
        onEditDivision: (item) => setDialog({ kind: "division", item }),
        onRemoveDivision: (d) => setRemoving({ kind: "division", id: d.id, name: d.name }),
        onAddPosition: (divisionId) => setDialog({ kind: "position", item: null, divisionId }),
        onEditPosition: (item) => setDialog({ kind: "position", item, divisionId: item.division_id ?? null }),
        onRemovePosition: (p) => setRemoving({ kind: "position", id: p.position_id, name: p.name }),
      }}
      dialog={dialog}
      removing={removing}
      onCloseDialog={() => setDialog(null)}
      onCloseRemove={() => setRemoving(null)}
    />
  );
}
