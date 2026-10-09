import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { FilePreview } from "@/components/molecules/FilePreview";
import { SelectField, TextAreaField } from "@/components/molecules/Field";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { reviewSchema, type ReviewValues } from "@/schemas/attendanceSchemas";
import { useAttendanceAction, type Attendance } from "@/services/attendanceService";
import { AttendanceFormDialog } from "./AttendanceFormDialog";

/** Finance meninjau absensi di luar radius (POST /attendance/{id}/review). */
export function AttendanceReviewDialog({ item, onClose }: { item: Attendance; onClose: () => void }) {
  const review = useAttendanceAction(async (body: components["schemas"]["ReviewRequest"]) =>
    (await api.post(`/attendance/${item.id}/review`, body)).data,
  );
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
      <p className="mb-1 text-sm font-medium">{item.employee_name}</p>
      <p className="mb-3 text-sm text-mist">
        {item.site_label} · {Math.round(item.distance_m)} m · masuk {formatDateTime(item.check_in_at)}
      </p>
      {item.offline && (
        <div role="status" className="mb-3 rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
          <p className="font-medium">Absen luring (direkam tanpa sinyal, dikirim saat online)</p>
          {item.offline_note && <p>Catatan server: {item.offline_note}</p>}
          {item.check_out_requested_at && (
            <p>
              Absen pulang {formatDateTime(item.check_out_requested_at)} berlaku bila absensi ini disetujui.
            </p>
          )}
        </div>
      )}
      {item.check_out_outside && (
        <div role="status" className="mb-3 rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
          <p className="font-medium">
            Pulang di luar radius ({Math.round(item.check_out_distance_m ?? 0)} m dari lokasi)
          </p>
          {item.check_out_explanation && <p>Penjelasan: {item.check_out_explanation}</p>}
          {item.check_out_selfie_file_id && (
            <div className="mt-2">
              <FilePreview fileId={item.check_out_selfie_file_id} fileName="Swafoto pulang" />
            </div>
          )}
        </div>
      )}
      {item.selfie_file_id ? (
        <div className="mb-3">
          <p className="mb-1 text-sm font-medium">Swafoto</p>
          <FilePreview fileId={item.selfie_file_id} fileName="Swafoto absen" />
        </div>
      ) : (
        <p className="mb-3 text-sm text-mist">Tanpa swafoto.</p>
      )}
      {(item.face_result || item.check_out_face_result) && (
        <div role="status" className="mb-3 rounded-control border border-line bg-surface p-3 text-sm">
          <p className="font-medium">Verifikasi Wajah (Server)</p>
          {item.face_result && (
            <p className="text-mist">
              Masuk: <span className="font-medium text-foreground">{item.face_result}</span>
              {item.face_similarity !== null && item.face_similarity !== undefined
                ? ` · Kemiripan: ${(item.face_similarity * 100).toFixed(1)}%`
                : ""}
            </p>
          )}
          {item.check_out_face_result && (
            <p className="text-mist">
              Pulang: <span className="font-medium text-foreground">{item.check_out_face_result}</span>
              {item.check_out_face_similarity !== null && item.check_out_face_similarity !== undefined
                ? ` · Kemiripan: ${(item.check_out_face_similarity * 100).toFixed(1)}%`
                : ""}
            </p>
          )}
        </div>
      )}
      <p className="mb-3 text-sm">Penjelasan karyawan: {item.explanation ?? "belum diisi"}</p>
      <SelectField label="Keputusan" {...register("decision")}>
        <option value="APPROVE">Setujui</option>
        <option value="REJECT">Tolak</option>
      </SelectField>
      <TextAreaField label="Catatan pemeriksaan" error={errors.note?.message} {...register("note")} />
    </AttendanceFormDialog>
  );
}
