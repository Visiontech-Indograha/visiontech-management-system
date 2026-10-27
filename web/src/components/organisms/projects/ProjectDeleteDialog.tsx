import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { useDeleteProject, type Project } from "@/services/projectService";

export function ProjectDeleteDialog({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const remove = useDeleteProject();
  const [formError, setFormError] = useState<string | null>(null);

  const handleDelete = async () => {
    setFormError(null);
    try {
      await remove.mutateAsync(project.project_id);
      toast.success(`Proyek ${project.project_title} berhasil diarsipkan.`);
      onClose();
    } catch {
      setFormError("Gagal menghapus proyek. Proyek yang sudah memiliki rencana kerja harian atau order tidak dapat dihapus.");
    }
  };

  return (
    <VmsDialog
      open
      title="Hapus / Batalkan Proyek"
      onClose={onClose}
      footer={
        <div className="flex items-center justify-end gap-2 w-full">
          <ActionButton variant="outline" onClick={onClose} disabled={remove.isPending}>
            Batal
          </ActionButton>
          <ActionButton
            type="button"
            variant="destructive"
            disabled={remove.isPending}
            onClick={handleDelete}
          >
            {remove.isPending ? "Memproses..." : "Ya, Hapus Proyek"}
          </ActionButton>
        </div>
      }
    >
      <TextBlock className="mb-2 text-sm text-foreground">
        Apakah Anda yakin ingin membatalkan/menghapus proyek{" "}
        <TextBlock as="strong" className="text-primary font-semibold">
          {project.project_title}
        </TextBlock>{" "}
        (SPK: {project.spk_number})?
      </TextBlock>
      {project.daily_plan_count > 0 && (
        <TextBlock className="mb-3 text-xs text-danger">
          Peringatan: Terdapat {project.daily_plan_count} rencana kerja harian yang tertaut ke proyek ini.
        </TextBlock>
      )}
      {formError && <FormErrorText message={formError} />}
    </VmsDialog>
  );
}
