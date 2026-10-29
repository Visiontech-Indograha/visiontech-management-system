import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { StyledInput, StyledLabel } from "@/components/molecules/InputControls";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useSession } from "@/stores/sessionStore";

/**
 * Tombol hapus permanen (docs/41 §5): hanya tampil bila pengguna punya izin `delete:any` (SUPER_ADMIN) dan
 * baru jalan setelah pengguna mengetik "HAPUS". `onDelete` memanggil API; daftar terkait di-refresh di sana.
 */
export function DeleteConfirmButton({ label, title, description, successText, onDelete }: {
  label: string;
  title: string;
  description: string;
  successText: string;
  onDelete: () => Promise<unknown>;
}) {
  const allowed = !!useSession().me?.permissions.includes("delete:any");
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!allowed) return null;

  const close = () => {
    if (busy) return; // jangan tutup selagi penghapusan berjalan
    setOpen(false);
    setTyped("");
    setError(null);
  };
  const confirm = async () => {
    setBusy(true);
    setError(null);
    try {
      await onDelete();
      toast.success(successText);
      setOpen(false);
      setTyped("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <ActionButton variant="outline" onClick={() => setOpen(true)}>
        {label}
      </ActionButton>
      <VmsDialog
        open={open}
        title={title}
        onClose={close}
        footer={
          <>
            <ActionButton variant="outline" onClick={close} disabled={busy}>
              Batal
            </ActionButton>
            <ActionButton onClick={confirm} disabled={busy || typed !== "HAPUS"}>
              Hapus permanen
            </ActionButton>
          </>
        }
      >
        <TextBlock className="mb-3 text-sm">{description} Data yang dihapus tidak bisa dikembalikan.</TextBlock>
        <FormErrorText message={error} className="mb-3" />
        <StyledLabel htmlFor="delete-confirm">Ketik HAPUS untuk melanjutkan</StyledLabel>
        <StyledInput id="delete-confirm" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
      </VmsDialog>
    </>
  );
}
