import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextAreaField } from "@/components/molecules/Field";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { useReviewLeave, type LeaveRequest } from "@/services/leaveService";

export function LeaveReviewDialog({
  leave,
  onClose,
}: {
  leave: LeaveRequest;
  onClose: () => void;
}) {
  const review = useReviewLeave();
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const handleReview = async (decision: "APPROVED" | "REJECTED") => {
    setFormError(null);
    if (decision === "REJECTED" && !note.trim()) {
      setFormError("Catatan/alasan penolakan wajib diisi jika menolak permohonan.");
      return;
    }

    try {
      await review.mutateAsync({
        leaveId: leave.leave_id,
        body: {
          decision,
          note: note.trim() || undefined,
        },
      });
      toast.success(
        decision === "APPROVED"
          ? `Permohonan cuti ${leave.employee_name} disetujui.`
          : `Permohonan cuti ${leave.employee_name} ditolak.`
      );
      onClose();
    } catch {
      setFormError("Gagal memproses permohonan cuti.");
    }
  };

  return (
    <VmsDialog
      open
      title="Tinjau Permohonan Cuti / Izin"
      onClose={onClose}
      footer={
        <div className="flex items-center justify-between w-full">
          <ActionButton variant="outline" onClick={onClose} disabled={review.isPending}>
            Batal
          </ActionButton>
          <div className="flex items-center gap-2">
            <ActionButton
              type="button"
              variant="destructive"
              disabled={review.isPending}
              onClick={() => handleReview("REJECTED")}
            >
              {review.isPending ? "Memproses..." : "Tolak Permohonan"}
            </ActionButton>
            <ActionButton
              type="button"
              variant="default"
              disabled={review.isPending}
              onClick={() => handleReview("APPROVED")}
            >
              {review.isPending ? "Memproses..." : "Setujui Permohonan"}
            </ActionButton>
          </div>
        </div>
      }
    >
      <div className="space-y-3 mb-4">
        <div className="p-3 rounded-control bg-hover space-y-1 text-xs">
          <div>
            <TextBlock as="span">
              Karyawan:{" "}
              <TextBlock as="strong" className="text-foreground">
                {leave.employee_name}
              </TextBlock>{" "}
              {leave.division_name ? `(${leave.division_name})` : ""}
            </TextBlock>
          </div>
          <div>
            <TextBlock as="span">
              Jenis:{" "}
              <TextBlock as="strong" className="text-foreground">
                {leave.leave_type}
              </TextBlock>{" "}
              · Durasi:{" "}
              <TextBlock as="strong" className="text-foreground">
                {leave.total_days} Hari
              </TextBlock>
            </TextBlock>
          </div>
          <div>
            <TextBlock as="span">
              Rentang: {String(leave.start_date).slice(0, 10)} s/d {String(leave.end_date).slice(0, 10)}
            </TextBlock>
          </div>
          <div className="pt-1 text-mist">
            <TextBlock as="span">
              Alasan:{" "}
              <TextBlock as="span" className="text-foreground italic font-normal">
                "{leave.reason}"
              </TextBlock>
            </TextBlock>
          </div>
        </div>

        <TextAreaField
          label="Catatan Persetujuan / Alasan Penolakan"
          placeholder="Wajib diisi jika menolak pengajuan cuti..."
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </div>

      {formError && <FormErrorText message={formError} />}
    </VmsDialog>
  );
}
