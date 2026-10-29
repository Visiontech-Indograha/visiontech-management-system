import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextAreaField } from "@/components/molecules/Field";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { LEAVE_TYPE_LABEL, useCancelLeave, type LeaveRequest } from "@/services/leaveService";

/** Pembatalan cuti yang sudah disetujui; alasan wajib diisi dan dicatat di permohonan. */
export function CancelLeaveDialog({
  leave,
  onClose,
}: {
  leave: LeaveRequest;
  onClose: () => void;
}) {
  const cancel = useCancelLeave();
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const handleCancel = async () => {
    setFormError(null);
    if (reason.trim().length < 3) {
      setFormError("Alasan pembatalan wajib diisi (minimal 3 karakter).");
      return;
    }
    try {
      await cancel.mutateAsync({ leaveId: leave.leave_id, reason: reason.trim() });
      toast.success(`Cuti ${leave.employee_name} dibatalkan.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err, "Gagal membatalkan cuti."));
    }
  };

  return (
    <VmsDialog
      open
      title="Batalkan Cuti"
      onClose={onClose}
      footer={
        <div className="flex items-center justify-between w-full">
          <ActionButton variant="outline" onClick={onClose} disabled={cancel.isPending}>
            Tutup
          </ActionButton>
          <ActionButton type="button" variant="destructive" disabled={cancel.isPending} onClick={handleCancel}>
            {cancel.isPending ? "Memproses..." : "Batalkan Cuti"}
          </ActionButton>
        </div>
      }
    >
      <div className="space-y-3 mb-4">
        <div className="p-3 rounded-control bg-hover space-y-1 text-xs">
          <TextBlock as="p">
            Karyawan: <TextBlock as="strong" className="text-foreground">{leave.employee_name}</TextBlock>
          </TextBlock>
          <TextBlock as="p">
            Jenis: {LEAVE_TYPE_LABEL[leave.leave_type] ?? leave.leave_type} · Rentang:{" "}
            {formatDate(String(leave.start_date))} s/d {formatDate(String(leave.end_date))}
          </TextBlock>
        </div>
        <TextAreaField
          label="Alasan Pembatalan"
          placeholder="Contoh: rencana cuti berubah, sudah masuk kerja..."
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <TextBlock as="p" className="text-xs text-mist">
          Absensi kembali diizinkan pada hari-hari cuti ini. Kuota cuti tahunan dikembalikan bila berlaku.
        </TextBlock>
      </div>
      {formError && <FormErrorText message={formError} />}
    </VmsDialog>
  );
}
