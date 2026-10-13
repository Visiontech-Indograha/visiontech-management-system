import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useDeactivateWorkType, type WorkType } from "@/services/workTypeService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Konfirmasi menonaktifkan jenis pekerjaan (rencana kerja lama tetap utuh). */
export function WorkTypeDeactivateDialog({ type, onClose }: { type: WorkType; onClose: () => void }) {
  const remove = useDeactivateWorkType();
  const confirm = async () => {
    try {
      await remove.mutateAsync(type.id);
      toast.success("Jenis pekerjaan dinonaktifkan.");
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <VmsDialog
      open
      title="Nonaktifkan jenis pekerjaan?"
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={remove.isPending}>
            Batal
          </ActionButton>
          <ActionButton variant="destructive" onClick={confirm} disabled={remove.isPending}>
            Nonaktifkan
          </ActionButton>
        </>
      }
    >
      <TextBlock className="text-sm">
        <TextBlock as="strong" className="text-ink">{type.name}</TextBlock> tidak akan ditawarkan lagi untuk rencana kerja baru. Rencana kerja yang
        sudah memakainya tetap utuh.
      </TextBlock>
    </VmsDialog>
  );
}
