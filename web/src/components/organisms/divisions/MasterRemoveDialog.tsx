import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useDeleteDivision, useDeletePosition, type RemoveTarget } from "@/services/divisionAdminService";


/** Konfirmasi hapus divisi atau jabatan. Bila masih dipakai, pesan awam dari API ditampilkan apa adanya. */
export function MasterRemoveDialog({ target, onClose }: { target: RemoveTarget; onClose: () => void }) {
  const delDivision = useDeleteDivision();
  const delPosition = useDeletePosition();
  const busy = delDivision.isPending || delPosition.isPending;
  const label = target.kind === "division" ? "divisi" : "jabatan";
  const confirm = async () => {
    try {
      await (target.kind === "division" ? delDivision : delPosition).mutateAsync(target.id);
      toast.success(`${label === "divisi" ? "Divisi" : "Jabatan"} dihapus.`);
      onClose();
    } catch (err) {
      toast.error(errorMessage(err, `Gagal menghapus ${label}. Coba lagi.`));
    }
  };
  return (
    <VmsDialog
      open
      title={`Hapus ${label}?`}
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={busy}>Batal</ActionButton>
          <ActionButton variant="destructive" onClick={confirm} disabled={busy}>Hapus</ActionButton>
        </>
      }
    >
      <TextBlock className="text-sm">
        <TextBlock as="strong" className="text-ink">{target.name}</TextBlock> akan dihapus dari daftar. Bila masih dipakai tim atau karyawan,
        {" "}penghapusan ditolak dan Anda perlu memindahkannya dulu.
      </TextBlock>
    </VmsDialog>
  );
}
