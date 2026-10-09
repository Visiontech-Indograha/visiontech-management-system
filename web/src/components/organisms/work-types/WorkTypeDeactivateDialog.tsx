import { toast } from "sonner";
import { Button } from "@/components/atoms/Button";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useDeactivateWorkType, type WorkType } from "@/services/workTypeService";

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
          <Button variant="outline" onClick={onClose} disabled={remove.isPending}>
            Batal
          </Button>
          <Button variant="destructive" onClick={confirm} disabled={remove.isPending}>
            Nonaktifkan
          </Button>
        </>
      }
    >
      <p className="text-sm">
        <strong className="text-ink">{type.name}</strong> tidak akan ditawarkan lagi untuk rencana kerja baru. Rencana kerja yang
        sudah memakainya tetap utuh.
      </p>
    </VmsDialog>
  );
}
