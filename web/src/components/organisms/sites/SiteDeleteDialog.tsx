import { toast } from "sonner";
import { Button } from "@/components/atoms/Button";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { useDeleteSite, type Site } from "@/services/siteService";

/** Konfirmasi hapus lokasi kerja (DELETE /sites/{id}). */
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
          <Button variant="outline" onClick={onClose} disabled={remove.isPending}>
            Batal
          </Button>
          <Button variant="destructive" onClick={confirm} disabled={remove.isPending}>
            {remove.isPending ? "Menghapus..." : "Hapus"}
          </Button>
        </>
      }
    >
      <p>
        Hapus <strong>{site.name}</strong>? Lokasi ini tidak bisa dipakai lagi untuk absensi.
      </p>
    </VmsDialog>
  );
}
