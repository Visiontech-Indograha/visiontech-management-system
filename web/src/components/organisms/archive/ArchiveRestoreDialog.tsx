import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useRestoreArchived, type ArchiveItem } from "@/services/archiveService";

/** Konfirmasi pulihkan. Bila ditolak (409), pesan awam dari API tampil di dalam dialog beserta cara memperbaikinya. */
export function ArchiveRestoreDialog({ slug, moduleLabel, item, onClose }: {
  slug: string;
  moduleLabel: string;
  item: ArchiveItem;
  onClose: () => void;
}) {
  const restore = useRestoreArchived(slug);
  const busy = restore.isPending;
  const [problem, setProblem] = useState<string | null>(null);
  const confirm = async () => {
    setProblem(null);
    try {
      await restore.mutateAsync(item.id);
      toast.success(`${item.name} sudah dipulihkan.`);
      onClose();
    } catch (err) {
      setProblem(errorMessage(err, "Data belum bisa dipulihkan. Coba lagi sebentar lagi."));
    }
  };
  return (
    <VmsDialog
      open
      title={`Pulihkan ${moduleLabel.toLowerCase()}?`}
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={busy}>Batal</ActionButton>
          <ActionButton onClick={confirm} pending={busy} pendingText="Memulihkan...">Pulihkan</ActionButton>
        </>
      }
    >
      <TextBlock className="text-sm">
        <TextBlock as="strong" className="text-ink">{item.name}</TextBlock> akan dikembalikan ke daftar {moduleLabel.toLowerCase()} yang aktif.
      </TextBlock>
      {problem && (
        <TextBlock role="alert" className="mt-3 rounded-control border border-warning-border bg-warning-bg p-3 text-sm text-warning">
          {problem}
        </TextBlock>
      )}
    </VmsDialog>
  );
}
