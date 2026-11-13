import { useState } from "react";
import { formatDate } from "@/lib/format";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { CheckControl } from "@/components/molecules/CheckControl";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextAreaField } from "@/components/molecules/Field";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useReviewLeave, type LeaveRequest, LEAVE_TYPE_LABEL } from "@/services/leaveService";

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
  const [acknowledged, setAcknowledged] = useState(false);
  const conflicts = leave.conflicts ?? [];
  const blockedByConflict = conflicts.length > 0 && !acknowledged;

  const handleReview = async (decision: "APPROVED" | "REJECTED") => {
    setFormError(null);
    if (decision === "REJECTED" && !note.trim()) {
      setFormError("Catatan/alasan penolakan wajib diisi jika menolak permohonan.");
      return;
    }
    if (decision === "APPROVED" && blockedByConflict) {
      setFormError("Centang konfirmasi konflik jadwal sebelum menyetujui permohonan ini.");
      return;
    }

    try {
      await review.mutateAsync({
        leaveId: leave.leave_id,
        body: {
          decision,
          note: note.trim() || undefined,
          ...(decision === "APPROVED" && conflicts.length > 0 ? { acknowledge_conflicts: true } : {}),
        },
      });
      toast.success(
        decision === "APPROVED"
          ? `Permohonan cuti ${leave.employee_name} disetujui.`
          : `Permohonan cuti ${leave.employee_name} ditolak.`
      );
      onClose();
    } catch (err) {
      setFormError(errorMessage(err, "Gagal memproses permohonan cuti."));
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
              disabled={review.isPending || blockedByConflict}
              onClick={() => handleReview("APPROVED")}
            >
              {review.isPending ? "Memproses..." : "Setujui Permohonan"}
            </ActionButton>
          </div>
        </div>
      }
    >
      <div className="space-y-3 mb-4">
        {conflicts.length > 0 && (
          <div role="alert" className="rounded-control border border-amber-500/40 bg-amber-500/10 p-3 space-y-2 text-xs">
            <TextBlock className="font-semibold text-foreground">
              Peringatan: pemohon terjadwal di tim pada hari cuti
            </TextBlock>
            {conflicts.map((c) => (
              <TextBlock key={c.plan_id} className="block text-foreground">
                {`• ${c.team_name} · ${formatDate(c.work_date)} (${c.status === "ONGOING" ? "berjalan" : "disetujui"})`}
              </TextBlock>
            ))}
            <div className="flex items-start gap-2 pt-1">
              <CheckControl
                aria-label="Konfirmasi konflik jadwal tim"
                checked={acknowledged}
                onCheckedChange={(v) => setAcknowledged(v === true)}
              />
              <TextBlock as="span">
                Saya memahami pemohon bertugas di tim pada tanggal tersebut dan tetap menyetujui cuti ini.
                PM divisi akan diberi tahu.
              </TextBlock>
            </div>
          </div>
        )}

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
                {LEAVE_TYPE_LABEL[leave.leave_type] ?? leave.leave_type}
              </TextBlock>{" "}
              · Durasi:{" "}
              <TextBlock as="strong" className="text-foreground">
                {leave.total_days} Hari
              </TextBlock>
            </TextBlock>
          </div>
          <div>
            <TextBlock as="span">
              Rentang: {formatDate(String(leave.start_date))} s/d {formatDate(String(leave.end_date))}
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
          label="Catatan persetujuan atau alasan penolakan"
          hint="Wajib diisi jika menolak pengajuan cuti."
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </div>

      {formError && <FormErrorText message={formError} />}
    </VmsDialog>
  );
}
