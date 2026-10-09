import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { TextAreaField } from "@/components/molecules/Field";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { explainSchema } from "@/schemas/attendanceSchemas";
import { useAttendanceAction, type Attendance } from "@/services/attendanceService";
import { AttendanceFormDialog } from "./AttendanceFormDialog";

/** Karyawan memberi penjelasan atas absensi sendiri yang perlu ditinjau (POST /attendance/{id}/explain). */
export function AttendanceExplainDialog({ item, onClose }: { item: Attendance; onClose: () => void }) {
  const explain = useAttendanceAction(async (body: components["schemas"]["ExplanationRequest"]) =>
    (await api.post(`/attendance/${item.id}/explain`, body)).data,
  );
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ explanation: string }>({ resolver: zodResolver(explainSchema), defaultValues: { explanation: item.explanation ?? "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await explain.mutateAsync(v);
      toast.success("Penjelasan ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AttendanceFormDialog title="Beri penjelasan" submitLabel="Kirim penjelasan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextAreaField label="Penjelasan" error={errors.explanation?.message} {...register("explanation")} />
    </AttendanceFormDialog>
  );
}
