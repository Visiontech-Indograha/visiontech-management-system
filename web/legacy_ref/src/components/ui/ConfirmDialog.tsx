import { Modal } from "./Modal";
import { Button } from "./Button";

interface ConfirmDialogProps {
  isOpen: boolean;
  title?: string;
  message: string;
  confirmLabel?: string;
  isConfirming?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Dialog konfirmasi generik untuk aksi merusak (hapus, batalkan, dsb).
 * Selalu tampilkan pesan spesifik (nama/judul record) di `message`, bukan teks generik.
 */
export const ConfirmDialog = ({
  isOpen,
  title = "Konfirmasi Hapus",
  message,
  confirmLabel = "Hapus",
  isConfirming = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) => {
  return (
    <Modal isOpen={isOpen} onClose={onCancel} title={title}>
      <p className="text-sm text-gray-600">{message}</p>
      <div className="mt-6 flex justify-end space-x-3">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Batal
        </button>
        <Button variant="danger" onClick={onConfirm} disabled={isConfirming}>
          {isConfirming ? "Menghapus..." : confirmLabel}
        </Button>
      </div>
    </Modal>
  );
};
