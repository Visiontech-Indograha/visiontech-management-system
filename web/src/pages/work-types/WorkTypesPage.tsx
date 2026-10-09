import { useState } from "react";
import { WorkTypeAddButton } from "@/components/organisms/work-types/WorkTypeAddButton";
import { WorkTypeDeactivateDialog } from "@/components/organisms/work-types/WorkTypeDeactivateDialog";
import { WorkTypeFormDialog } from "@/components/organisms/work-types/WorkTypeFormDialog";
import { WorkTypeList } from "@/components/organisms/work-types/WorkTypeList";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { useWorkTypes, type WorkType } from "@/services/workTypeService";

/** Jenis pekerjaan + template foto laporan (T9): GET/POST/PUT/DELETE /work-types, izin create:plan (PM/OPS). */
export function WorkTypesPage() {
  const types = useWorkTypes(true);
  const [editing, setEditing] = useState<WorkType | "new" | null>(null);
  const [removing, setRemoving] = useState<WorkType | null>(null);

  return (
    <PageTemplate title="Jenis pekerjaan" action={<WorkTypeAddButton onAdd={() => setEditing("new")} />}>
      <WorkTypeList types={types} onAdd={() => setEditing("new")} onEdit={setEditing} onDeactivate={setRemoving} />
      {editing && <WorkTypeFormDialog type={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
      {removing && <WorkTypeDeactivateDialog type={removing} onClose={() => setRemoving(null)} />}
    </PageTemplate>
  );
}
