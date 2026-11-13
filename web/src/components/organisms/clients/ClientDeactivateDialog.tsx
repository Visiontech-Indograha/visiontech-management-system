import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useDeleteClient, type Client } from "@/services/clientService";

export function ClientDeactivateDialog({
  client,
  onClose,
}: {
  client: Client;
  onClose: () => void;
}) {
  const remove = useDeleteClient();
  const [formError, setFormError] = useState<string | null>(null);

  const handleDeactivate = async () => {
    setFormError(null);
    try {
      await remove.mutateAsync(client.client_id);
      toast.success(`Klien ${client.name} berhasil diarsipkan.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err, "Klien belum bisa diarsipkan. Klien yang memiliki proyek aktif tidak dapat dihapus."));
    }
  };

  return (
    <VmsDialog
      open
      title="Hapus / Arsipkan Klien"
      onClose={onClose}
      footer={
        <div className="flex items-center justify-end gap-2 w-full">
          <ActionButton variant="outline" onClick={onClose} disabled={remove.isPending}>
            Batal
          </ActionButton>
          <ActionButton
            type="button"
            variant="destructive"
            pending={remove.isPending} pendingText="Memproses..."
            onClick={handleDeactivate}
          >
            {"Ya, Hapus / Arsipkan"}
          </ActionButton>
        </div>
      }
    >
      <TextBlock className="mb-2 text-sm text-foreground">
        Apakah Anda yakin ingin menghapus atau mengarsipkan klien{" "}
        <TextBlock as="strong" className="text-primary font-semibold">
          {client.name}
        </TextBlock>{" "}
        ({client.client_code})?
      </TextBlock>
      {client.project_count > 0 && (
        <TextBlock className="mb-3 text-xs text-danger">
          Peringatan: Klien ini memiliki {client.project_count} proyek terdaftar. Penghapusan akan ditolak bila ada riwayat aktif.
        </TextBlock>
      )}
      {formError && <FormErrorText message={formError} />}
    </VmsDialog>
  );
}
