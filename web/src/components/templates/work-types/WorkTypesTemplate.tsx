import type { UseQueryResult } from "@tanstack/react-query";
import { WorkTypeAddButton } from "@/components/organisms/work-types/WorkTypeAddButton";
import { WorkTypeDeactivateDialog } from "@/components/organisms/work-types/WorkTypeDeactivateDialog";
import { WorkTypeFormDialog } from "@/components/organisms/work-types/WorkTypeFormDialog";
import { WorkTypeList } from "@/components/organisms/work-types/WorkTypeList";
import type { ListControls } from "@/hooks/usePagedList";
import type { Paged } from "@/lib/paged";
import type { WorkType } from "@/services/workTypeService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Jenis pekerjaan": daftar jenis + dialog tambah/ubah/nonaktifkan. */
export function WorkTypesTemplate({ controls, types, editing, removing, onAdd, onEdit, onDeactivate, onCloseEdit, onCloseRemove }: {
  controls: ListControls;
  types: UseQueryResult<Paged<WorkType>>;
  editing: WorkType | "new" | null;
  removing: WorkType | null;
  onAdd: () => void;
  onEdit: (type: WorkType) => void;
  onDeactivate: (type: WorkType) => void;
  onCloseEdit: () => void;
  onCloseRemove: () => void;
}) {
  return (
    <PageTemplate title="Jenis pekerjaan" action={<WorkTypeAddButton onAdd={onAdd} />}>
      <WorkTypeList controls={controls} types={types} onAdd={onAdd} onEdit={onEdit} onDeactivate={onDeactivate} />
      {editing && <WorkTypeFormDialog type={editing === "new" ? null : editing} onClose={onCloseEdit} />}
      {removing && <WorkTypeDeactivateDialog type={removing} onClose={onCloseRemove} />}
    </PageTemplate>
  );
}
