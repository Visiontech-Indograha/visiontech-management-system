import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { TextField, SelectField, TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { uploadFiles } from "@/services/uploadService";
import { useLeaveMutation, type LeaveCreateInput } from "@/services/leaveService";
import { useSession } from "@/stores/sessionStore";

function calculateWorkingDays(startStr: string, endStr: string): number {
  const start = new Date(startStr);
  const end = new Date(endStr);
  let days = 0;
  const cur = new Date(start);
  while (cur <= end) {
    if (cur.getDay() !== 0) {
      days++;
    }
    cur.setDate(cur.getDate() + 1);
  }
  return days;
}

export function LeaveApplyDialog({
  onClose,
}: {
  onClose: () => void;
}) {
  const mutation = useLeaveMutation();
  const { me } = useSession();
  const [formError, setFormError] = useState<string | null>(null);
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

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

    const effectiveDays = calculateWorkingDays(values.start_date, values.end_date);
    if (effectiveDays <= 0) {
      setFormError("Permohonan cuti harus mencakup minimal 1 hari kerja efektif (bukan hari Minggu saja).");
      return;
    }

    try {
      let attachment_file_id: string | undefined = undefined;
      if (values.leave_type === "SICK" && attachmentFile) {
        setIsUploading(true);
        const [uploadedId] = await uploadFiles([attachmentFile]);
        attachment_file_id = uploadedId;
      }

      await mutation.mutateAsync({
        employee_id: me?.employee_id || undefined,
        leave_type: values.leave_type,
        start_date: values.start_date,
        end_date: values.end_date,
        reason: values.reason.trim(),
        attachment_file_id,
      });
      toast.success("Permohonan cuti / izin berhasil diajukan dan menunggu persetujuan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err, "Gagal mengajukan permohonan cuti. Periksa kuota cuti tahunan atau tanggal yang bentrok."));
    } finally {
      setIsUploading(false);
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
          busy={isSubmitting || isUploading}
          formId="leave-apply-form"
          submitLabel={isUploading ? "Mengunggah berkas..." : "Kirim Pengajuan"}
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
              Perkiraan durasi hari kerja:{" "}
              <TextBlock as="strong" className="text-foreground">
                {calculateWorkingDays(startDate, endDate)} hari
              </TextBlock>{" "}
              (tidak termasuk hari Minggu) ·{" "}
              {leaveType === "ANNUAL" ? "(akan dikurangi dari kuota cuti tahunan)" : "(tidak memotong kuota tahunan)"}
            </TextBlock>
          </div>
        )}

        {leaveType === "SICK" && (
          <div className="space-y-1.5 rounded-control border border-line bg-hover/20 p-3">
            <TextField
              label="Surat Keterangan Dokter (Opsional / Disarankan)"
              type="file"
              accept=".jpg,.jpeg,.png,.pdf"
              onChange={(e) => {
                const file = e.target.files?.[0];
                setAttachmentFile(file ?? null);
              }}
            />
            <TextBlock className="text-2xs text-mist">
              Format: JPG, PNG, atau PDF (maks. 10 MB). Lampirkan surat dokter untuk mempercepat verifikasi oleh HR/GA.
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
