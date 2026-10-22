import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { useDeleteSite, type Site } from "@/services/siteService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Konfirmasi hapus lokasi kerja (DELETE /offices/{id}). */
export function SiteDeleteDialog({ site, onClose }: { site: Site; onClose: () => void }) {
  const remove = useDeleteSite();
  const confirm = async () => {
    try {
      await remove.mutateAsync(site.id);
      toast.success("Lokasi kerja dihapus.");
      onClose();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };
  return (
    <VmsDialog
      open
      title="Hapus lokasi kerja"
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={remove.isPending}>
            Batal
          </ActionButton>
          <ActionButton variant="destructive" onClick={confirm} disabled={remove.isPending}>
            {remove.isPending ? "Menghapus..." : "Hapus"}
          </ActionButton>
        </>
      }
    >
      <TextBlock>
        Hapus <TextBlock as="strong">{site.name}</TextBlock>? Lokasi ini tidak bisa dipakai lagi untuk absensi.
      </TextBlock>
    </VmsDialog>
  );
}
