import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { TextField, SelectField, TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useLeaveMutation, type LeaveCreateInput } from "@/services/leaveService";
import { useSession } from "@/stores/sessionStore";

export function LeaveApplyDialog({
  onClose,
}: {
  onClose: () => void;
}) {
  const mutation = useLeaveMutation();
  const { me } = useSession();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<LeaveCreateInput>({
    defaultValues: {
      leave_type: "ANNUAL",
      start_date: new Date().toISOString().slice(0, 10),
      end_date: new Date().toISOString().slice(0, 10),
      reason: "",
    },
  });

  const startDate = useWatch({ control, name: "start_date" });
  const endDate = useWatch({ control, name: "end_date" });
  const leaveType = useWatch({ control, name: "leave_type" });

  const onSubmit = async (values: LeaveCreateInput) => {
    setFormError(null);
    if (new Date(values.end_date) < new Date(values.start_date)) {
      setFormError("Tanggal selesai tidak boleh sebelum tanggal mulai.");
      return;
    }

    try {
      await mutation.mutateAsync({
        employee_id: me?.employee_id || undefined,
        leave_type: values.leave_type,
        start_date: values.start_date,
        end_date: values.end_date,
        reason: values.reason.trim(),
      });
      toast.success("Permohonan cuti / izin berhasil diajukan dan menunggu persetujuan.");
      onClose();
    } catch {
      setFormError("Gagal mengajukan permohonan cuti. Periksa kuota cuti tahunan atau tanggal yang bentrok.");
    }
  };

  return (
    <VmsDialog
      open
      title="Ajukan Cuti / Izin Kerja"
      onClose={onClose}
      footer={
        <DialogActions
          onCancel={onClose}
          busy={isSubmitting}
          formId="leave-apply-form"
          submitLabel="Kirim Pengajuan"
        />
      }
    >
      <TextBlock className="mb-4 text-sm text-mist">
        Isi formulir permohonan cuti tahunan, izin sakit, atau izin khusus lainnya.
      </TextBlock>
      <FormBlock id="leave-apply-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}

        <SelectField
          label="Jenis Cuti / Izin"
          error={errors.leave_type?.message}
          {...register("leave_type", { required: "Jenis cuti wajib dipilih." })}
        >
          <ControlOption value="ANNUAL">Cuti Tahunan (Memotong Kuota Tahunan)</ControlOption>
          <ControlOption value="SICK">Izin Sakit (Melampirkan Surat Dokter)</ControlOption>
          <ControlOption value="MATERNITY">Cuti Melahirkan / Bersalin</ControlOption>
          <ControlOption value="UNPAID">Cuti di Luar Tanggungan (Unpaid)</ControlOption>
          <ControlOption value="OTHER">Izin Khusus / Keperluan Mendesak</ControlOption>
        </SelectField>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <TextField
            label="Tanggal Mulai"
            type="date"
            error={errors.start_date?.message}
            {...register("start_date", { required: "Tanggal mulai wajib diisi." })}
          />

          <TextField
            label="Tanggal Selesai"
            type="date"
            error={errors.end_date?.message}
            {...register("end_date", { required: "Tanggal selesai wajib diisi." })}
          />
        </div>

        {startDate && endDate && new Date(endDate) >= new Date(startDate) && (
          <div className="p-2.5 rounded-control bg-hover text-xs text-mist">
            <TextBlock as="span">
              Perkiraan durasi:{" "}
              <TextBlock as="strong" className="text-foreground">
                {Math.max(1, Math.round((new Date(endDate).getTime() - new Date(startDate).getTime()) / 86400000) + 1)} hari
              </TextBlock>{" "}
              {leaveType === "ANNUAL" ? "(akan dikurangi dari kuota cuti tahunan)" : "(tidak memotong kuota tahunan)"}
            </TextBlock>
          </div>
        )}

        <TextAreaField
          label="Alasan Pengajuan"
          placeholder="Jelaskan alasan atau keperluan permohonan cuti..."
          rows={3}
          error={errors.reason?.message}
          {...register("reason", {
            required: "Alasan pengajuan cuti wajib diisi.",
            minLength: { value: 5, message: "Minimal 5 karakter alasan." },
          })}
        />
      </FormBlock>
    </VmsDialog>
  );
}
