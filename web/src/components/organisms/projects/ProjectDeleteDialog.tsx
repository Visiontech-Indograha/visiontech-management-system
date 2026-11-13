import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useDeleteProject, type Project } from "@/services/projectService";

/** Satu istilah untuk satu tindakan: "Arsipkan". API menolak arsip bila proyek sudah punya jadwal atau order. */
export function ProjectDeleteDialog({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const remove = useDeleteProject();
  const [formError, setFormError] = useState<string | null>(null);
  const inUse = project.daily_plan_count > 0 || project.order_count > 0;

  const handleArchive = async () => {
    setFormError(null);
    try {
      await remove.mutateAsync(project.project_id);
      toast.success(`Proyek ${project.project_title} berhasil diarsipkan.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err, "Gagal mengarsipkan proyek. Coba lagi."));
    }
  };

  return (
    <VmsDialog
      open
      title="Arsipkan proyek"
      onClose={onClose}
      footer={
        <div className="flex items-center justify-end gap-2 w-full">
          <ActionButton variant="outline" onClick={onClose} disabled={remove.isPending}>
            Batal
          </ActionButton>
          {!inUse && (
            <ActionButton
              type="button"
              variant="destructive"
              pending={remove.isPending} pendingText="Memproses..."
              onClick={handleArchive}
            >
              {"Ya, arsipkan"}
            </ActionButton>
          )}
        </div>
      }
    >
      {inUse ? (
        <TextBlock className="mb-3 text-sm text-danger">
          Proyek {project.project_title} tidak dapat diarsipkan karena sudah memiliki {project.daily_plan_count} jadwal harian
          dan {project.order_count} order. Ubah statusnya saja.
        </TextBlock>
      ) : (
        <>
          <TextBlock className="mb-2 text-sm text-foreground">
            Arsipkan proyek{" "}
            <TextBlock as="strong" className="text-primary font-semibold">
              {project.project_title}
            </TextBlock>{" "}
            (SPK: {project.spk_number})?
          </TextBlock>
          <TextBlock className="mb-3 text-xs text-mist">
            Proyek yang diarsipkan disembunyikan dari daftar proyek dan tidak dipakai untuk jadwal atau order baru.
          </TextBlock>
        </>
      )}
      {formError && <FormErrorText message={formError} />}
    </VmsDialog>
  );
}
