import { useState } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { AttachmentPanel } from "@/components/organisms/AttachmentPanel";
import type { AttachmentKind } from "@/services/attachmentService";

/** Tombol "Lampiran" yang membuka daftar lampiran pengajuan dalam dialog. */
export function AttachmentButton({ kind, parentId, locked }: { kind: AttachmentKind; parentId: string; locked: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <ActionButton variant="outline" size="sm" onClick={() => setOpen(true)}>
        Lampiran
      </ActionButton>
      <VmsDialog open={open} title="Lampiran" size="md" onClose={() => setOpen(false)}>
        <AttachmentPanel kind={kind} parentId={parentId} locked={locked} />
      </VmsDialog>
    </>
  );
}
