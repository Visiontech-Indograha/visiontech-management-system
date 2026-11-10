import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { LEAVE_TYPE_LABEL, useCancelLeave, type LeaveRequest } from "@/services/leaveService";

/** Batalkan pengajuan cuti milik sendiri yang masih menunggu (tanpa alasan tertulis). */
export function WithdrawLeaveDialog({ leave, onClose }: { leave: LeaveRequest; onClose: () => void }) {
  const cancel = useCancelLeave();
  const [error, setError] = useState<string | null>(null);

  const confirm = async () => {
    setError(null);
    try {
      await cancel.mutateAsync({ leaveId: leave.leave_id });
      toast.success("Pengajuan dibatalkan.");
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Pengajuan belum bisa dibatalkan. Coba lagi."));
    }
  };

  return (
    <ConfirmDialog
      open
      title="Batalkan pengajuan?"
      message={`Pengajuan ${LEAVE_TYPE_LABEL[leave.leave_type] ?? leave.leave_type} tanggal ${formatDate(String(leave.start_date))} sampai ${formatDate(String(leave.end_date))} tidak akan diproses. Anda bisa mengajukan lagi nanti.`}
      confirmLabel="Ya, batalkan"
      danger
      busy={cancel.isPending}
      error={error}
      onConfirm={confirm}
      onClose={onClose}
    />
  );
}
