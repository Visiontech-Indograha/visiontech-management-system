import { useState } from "react";
import { WorkTypesTemplate } from "@/components/templates/work-types/WorkTypesTemplate";
import { useWorkTypes, type WorkType } from "@/services/workTypeService";

/** Jenis pekerjaan + template foto laporan (T9): GET/POST/PUT/DELETE /work-types, izin create:plan (PM/OPS). */
export function WorkTypesPage() {
  const types = useWorkTypes(true);
  const [editing, setEditing] = useState<WorkType | "new" | null>(null);
  const [removing, setRemoving] = useState<WorkType | null>(null);

  return (
    <WorkTypesTemplate
      types={types}
      editing={editing}
      removing={removing}
      onAdd={() => setEditing("new")}
      onEdit={setEditing}
      onDeactivate={setRemoving}
      onCloseEdit={() => setEditing(null)}
      onCloseRemove={() => setRemoving(null)}
    />
  );
}
