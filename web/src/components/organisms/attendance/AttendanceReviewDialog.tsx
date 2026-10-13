import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { FilePreview } from "@/components/molecules/FilePreview";
import { SelectField, TextAreaField } from "@/components/molecules/Field";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { reviewSchema, type ReviewValues } from "@/schemas/attendanceSchemas";
import { useAttendanceAction, type Attendance, reviewAttendance } from "@/services/attendanceService";
import { AttendanceFormDialog } from "./AttendanceFormDialog";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ControlOption } from "@/components/molecules/FormBlock";

/** Finance meninjau absensi di luar radius (POST /attendance/{id}/review). */
export function AttendanceReviewDialog({ item, onClose }: { item: Attendance; onClose: () => void }) {
  const review = useAttendanceAction((body: components["schemas"]["ReviewRequest"]) => reviewAttendance(item.id, body));
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReviewValues>({ resolver: zodResolver(reviewSchema), defaultValues: { decision: "APPROVE", note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await review.mutateAsync({ is_approved: v.decision === "APPROVE", note: v.note });
      toast.success(v.decision === "APPROVE" ? "Absensi disetujui." : "Absensi ditolak.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AttendanceFormDialog title="Tinjau absensi" submitLabel="Simpan keputusan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextBlock className="mb-1 text-sm font-medium">{item.employee_name}</TextBlock>
      <TextBlock className="mb-3 text-sm text-mist">
        {item.site_label} · {Math.round(item.distance_m)} m · masuk {formatDateTime(item.check_in_at)}
      </TextBlock>
      {item.offline && (
        <div role="status" className="mb-3 rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
          <TextBlock className="font-medium">Absen luring (direkam tanpa sinyal, dikirim saat online)</TextBlock>
          {item.offline_note && <TextBlock>Catatan server: {item.offline_note}</TextBlock>}
          {item.check_out_requested_at && (
            <TextBlock>
              Absen pulang {formatDateTime(item.check_out_requested_at)} berlaku bila absensi ini disetujui.
            </TextBlock>
          )}
        </div>
      )}
      {item.check_out_outside && (
        <div role="status" className="mb-3 rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
          <TextBlock className="font-medium">
            Pulang di luar radius ({Math.round(item.check_out_distance_m ?? 0)} m dari lokasi)
          </TextBlock>
          {item.check_out_explanation && <TextBlock>Penjelasan: {item.check_out_explanation}</TextBlock>}
          {item.check_out_selfie_file_id && (
            <div className="mt-2">
              <FilePreview fileId={item.check_out_selfie_file_id} fileName="Swafoto pulang" />
            </div>
          )}
        </div>
      )}
      {item.selfie_file_id ? (
        <div className="mb-3">
          <TextBlock className="mb-1 text-sm font-medium">Swafoto</TextBlock>
          <FilePreview fileId={item.selfie_file_id} fileName="Swafoto absen" />
        </div>
      ) : (
        <TextBlock className="mb-3 text-sm text-mist">Tanpa swafoto.</TextBlock>
      )}
      {(item.face_result || item.check_out_face_result) && (
        <div role="status" className="mb-3 rounded-control border border-line bg-surface p-3 text-sm">
          <TextBlock className="font-medium">Verifikasi Wajah (Server)</TextBlock>
          {item.face_result && (
            <TextBlock className="text-mist">
              Masuk: <TextBlock as="span" className="font-medium text-foreground">{item.face_result}</TextBlock>
              {item.face_similarity !== null && item.face_similarity !== undefined
                ? ` · Kemiripan: ${(item.face_similarity * 100).toFixed(1)}%`
                : ""}
            </TextBlock>
          )}
          {item.check_out_face_result && (
            <TextBlock className="text-mist">
              Pulang: <TextBlock as="span" className="font-medium text-foreground">{item.check_out_face_result}</TextBlock>
              {item.check_out_face_similarity !== null && item.check_out_face_similarity !== undefined
                ? ` · Kemiripan: ${(item.check_out_face_similarity * 100).toFixed(1)}%`
                : ""}
            </TextBlock>
          )}
        </div>
      )}
      <TextBlock className="mb-3 text-sm">Penjelasan karyawan: {item.explanation ?? "belum diisi"}</TextBlock>
      <SelectField label="Keputusan" {...register("decision")}>
        <ControlOption value="APPROVE">Setujui</ControlOption>
        <ControlOption value="REJECT">Tolak</ControlOption>
      </SelectField>
      <TextAreaField label="Catatan pemeriksaan" error={errors.note?.message} {...register("note")} />
    </AttendanceFormDialog>
  );
}
