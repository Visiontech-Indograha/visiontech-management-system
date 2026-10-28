import { useState } from "react";
import { WorkTypesTemplate } from "@/components/templates/work-types/WorkTypesTemplate";
import { useListControls } from "@/hooks/useListControls";
import { usePagedList } from "@/hooks/usePagedList";
import type { WorkType } from "@/services/workTypeService";

/** Jenis pekerjaan + template foto laporan (T9): GET/POST/PUT/DELETE /work-types, izin create:plan (PM/OPS). */
export function WorkTypesPage() {
  const controls = useListControls({ prefix: "jns_" });
  const types = usePagedList<WorkType>(["work-types"], "/work-types", controls, { all: true });
  const [editing, setEditing] = useState<WorkType | "new" | null>(null);
  const [removing, setRemoving] = useState<WorkType | null>(null);

  return (
    <WorkTypesTemplate
      controls={controls}
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
