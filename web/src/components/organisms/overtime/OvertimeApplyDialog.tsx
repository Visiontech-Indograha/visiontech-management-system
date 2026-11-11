import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { TextField, SelectField, TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { QueryState } from "@/components/molecules/QueryState";
import { useOnline } from "@/hooks/useOnline";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { useIdempotencyKey } from "@/lib/idempotency";
import { useDailyPlans, wibDate } from "@/services/dailyPlanService";
import { useCreateOvertime } from "@/services/overtimeService";

/** Batas sama dengan API: jam > 0 dan paling banyak 12; alasan wajib, paling banyak 1000 huruf. */
export const OVERTIME_MAX_HOURS = 12;
export const OVERTIME_REASON_MAX = 1000;

interface Values {
  daily_plan_id: string;
  hours: string;
  reason: string;
}

export function OvertimeApplyDialog({ onClose }: { onClose: () => void }) {
  const online = useOnline();
  const mutation = useCreateOvertime();
  const today = wibDate();
  const plans = useDailyPlans({ start: today, end: today });
  const ongoing = (plans.data ?? []).filter((p) => p.status === "ONGOING");
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<Values>({ defaultValues: { daily_plan_id: "", hours: "", reason: "" } });
  const allValues = useWatch({ control });
  const idem = useIdempotencyKey(JSON.stringify(allValues));

  const onSubmit = async (v: Values) => {
    setFormError(null);
    const hours = Number(v.hours);
    const reason = v.reason.trim();
    if (!(hours > 0 && hours <= OVERTIME_MAX_HOURS)) {
      setError("hours", { message: `Jam lembur harus lebih dari 0 dan paling banyak ${OVERTIME_MAX_HOURS} jam.` });
      return;
    }
    if (!reason) {
      setError("reason", { message: "Alasan lembur wajib diisi." });
      return;
    }
    try {
      await mutation.mutateAsync({ body: { daily_plan_id: v.daily_plan_id, hours, reason }, key: idem.key });
      idem.renew();
      toast.success("Lembur berhasil diajukan dan menunggu keputusan.");
      onClose();
    } catch (err) {
      if (applyFieldErrors(err, setError)) {
        setFormError("Periksa kolom yang ditandai.");
        return;
      }
      setFormError(errorMessage(err, "Lembur belum dapat diajukan. Coba lagi."));
    }
  };

  return (
    <VmsDialog
      dirty={isDirty}
      open
      title="Ajukan lembur"
      onClose={onClose}
      footer={
        <DialogActions
          onCancel={onClose}
          busy={isSubmitting || mutation.isPending || !online || ongoing.length === 0}
          formId="overtime-apply-form"
          submitLabel="Kirim pengajuan"
          busyLabel="Mengirim..."
        />
      }
    >
      <QueryState
        query={plans}
        errorText="Jadwal hari ini tidak dapat dimuat."
        empty={ongoing.length === 0}
        emptyText="Lembur diajukan dari jadwal yang sedang berjalan. Buka tab Jadwal kerja, pilih jadwal hari ini."
      >
        <FormBlock id="overtime-apply-form" onSubmit={handleSubmit(onSubmit)}>
          {!online && <FormErrorText message="Anda sedang offline. Sambungkan internet untuk mengirim lembur." />}
          {formError && <FormErrorText message={formError} />}
          <SelectField
            label="Jadwal kerja"
            error={errors.daily_plan_id?.message}
            {...register("daily_plan_id", { required: "Pilih jadwal kerja." })}
          >
            <ControlOption value="">Pilih jadwal</ControlOption>
            {ongoing.map((p) => (
              <ControlOption key={p.daily_plan_id} value={p.daily_plan_id}>
                {p.team_name} · {formatDate(p.work_date)}
              </ControlOption>
            ))}
          </SelectField>
          <TextField
            label="Lama lembur (jam)"
            type="number"
            inputMode="decimal"
            error={errors.hours?.message}
            {...register("hours", { required: "Isi lama lembur." })}
          />
          <TextAreaField
            label="Alasan"
            maxLength={OVERTIME_REASON_MAX}
            error={errors.reason?.message}
            {...register("reason", { required: "Alasan lembur wajib diisi.", maxLength: OVERTIME_REASON_MAX })}
          />
        </FormBlock>
      </QueryState>
    </VmsDialog>
  );
}
