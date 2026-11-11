import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { errorMessage } from "@/lib/errors";
import { useDeleteSite, type Site } from "@/services/siteService";

/** Konfirmasi hapus lokasi kerja (DELETE /offices/{id}). */
export function SiteDeleteDialog({ site, onClose }: { site: Site; onClose: () => void }) {
  const remove = useDeleteSite();
  const [error, setError] = useState<string | null>(null);
  const confirm = async () => {
    setError(null);
    try {
      await remove.mutateAsync(site.id);
      toast.success("Lokasi kerja dihapus.");
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Lokasi kerja belum bisa dihapus. Coba lagi."));
    }
  };
  return (
    <ConfirmDialog
      open
      title="Hapus lokasi kerja"
      message={`Hapus ${site.name}? Lokasi ini tidak bisa dipakai lagi untuk absensi.`}
      confirmLabel="Hapus"
      danger
      busy={remove.isPending}
      error={error}
      onConfirm={confirm}
      onClose={onClose}
    />
  );
}
