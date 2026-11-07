import type { ComponentProps } from "react";
import { DivisionAddButton } from "@/components/organisms/divisions/DivisionAddButton";
import { DivisionFormDialog } from "@/components/organisms/divisions/DivisionFormDialog";
import { DivisionList } from "@/components/organisms/divisions/DivisionList";
import { MasterRemoveDialog } from "@/components/organisms/divisions/MasterRemoveDialog";
import { PositionFormDialog } from "@/components/organisms/divisions/PositionFormDialog";
import type { DivisionDialog, RemoveTarget } from "@/services/divisionAdminService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Divisi dan jabatan": daftar + dialog tambah/ubah/hapus. */
export function DivisionsTemplate({ list, dialog, removing, onCloseDialog, onCloseRemove }: {
  list: ComponentProps<typeof DivisionList>;
  dialog: DivisionDialog | null;
  removing: RemoveTarget | null;
  onCloseDialog: () => void;
  onCloseRemove: () => void;
}) {
  return (
    <PageTemplate
      title="Divisi dan jabatan"
      description="Atur divisi, atasan divisi (OM dan PM), dan jabatan karyawan."
      action={list.canDivisions ? <DivisionAddButton onAdd={list.onAddDivision} /> : undefined}
    >
      <DivisionList {...list} />
      {dialog?.kind === "division" && <DivisionFormDialog division={dialog.item} onClose={onCloseDialog} />}
      {dialog?.kind === "position" && <PositionFormDialog position={dialog.item} divisionId={dialog.divisionId} onClose={onCloseDialog} />}
      {removing && <MasterRemoveDialog target={removing} onClose={onCloseRemove} />}
    </PageTemplate>
  );
}
