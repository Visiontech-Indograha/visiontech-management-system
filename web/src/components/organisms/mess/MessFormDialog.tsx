import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useIdempotencyKey } from "@/lib/idempotency";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextField, SelectField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { useCreateMessStay, useMessPlaces, useMessStays, type MessStay } from "@/services/messService";
import { useEmployees } from "@/services/employeeService";
import { useTeams } from "@/services/teamService";

const DAY_MS = 86_400_000;
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);
const dmy = (d: string) => d.split("-").reverse().join("-");

/** Tanggal (YYYY-MM-DD) dalam [start, end] ketika jumlah hunian APPROVED di mess ini sudah mencapai kapasitas. */
function fullOn(stays: MessStay[], messId: string, start: string, end: string, capacity: number): string[] {
  const out: string[] = [];
  for (let t = Date.parse(`${start}T00:00:00Z`); iso(t) <= end; t += DAY_MS) {
    const day = iso(t);
    const count = stays.filter((s) => s.mess_id === messId && s.stay_start_date <= day && s.stay_end_date >= day).length;
    if (count >= capacity) out.push(day);
  }
  return out;
}

const messSchema = z
  .object({
    employee_id: z.string().trim().min(1, "Karyawan wajib dipilih."),
    mess_id: z.string().trim().min(1, "Mess wajib dipilih."),
    team_id: z.string().trim().optional(),
    stay_start_date: z
      .string()
      .trim()
      .min(1, "Tanggal mulai inap wajib diisi."),
    stay_end_date: z
      .string()
      .trim()
      .min(1, "Tanggal selesai inap wajib diisi."),
  })
  .refine(
    (v) =>
      !v.stay_start_date ||
      !v.stay_end_date ||
      v.stay_end_date >= v.stay_start_date,
    {
      message: "Tanggal selesai tidak boleh sebelum tanggal mulai.",
      path: ["stay_end_date"],
    },
  );
type MessValues = z.infer<typeof messSchema>;

/** HR/GA menempatkan karyawan: mess dipilih dari daftar (bukan diketik), langsung disetujui. */
export function MessFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateMessStay();
  const places = useMessPlaces();
  const employeesQuery = useEmployees({ status: "active", page: 1, size: 100 });
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    control,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<MessValues>({
    resolver: zodResolver(messSchema),
    defaultValues: {
      employee_id: "",
      mess_id: "",
      team_id: "",
      stay_start_date: "",
      stay_end_date: "",
    },
  });

  const allValues = useWatch({ control });
  const idem = useIdempotencyKey(JSON.stringify(allValues));

  const employeeList = employeesQuery.data?.items ?? [];
  const placeList = places.data ?? [];
  const teams = useTeams();
  const [messId, startDate, endDate] = useWatch({
    control,
    name: ["mess_id", "stay_start_date", "stay_end_date"],
  });
  const place = placeList.find((p) => p.mess_id === messId);
  // Kapasitas per tanggal: hunian yang sudah disetujui pada mess ini dihitung per hari dalam rentang.
  const occupancy = useMessStays(
    messId && startDate && endDate && endDate >= startDate
      ? { start: startDate, end: endDate, status: "APPROVED" }
      : undefined,
  );
  const fullDays = place?.capacity && startDate && endDate && endDate >= startDate
    ? fullOn(occupancy.data ?? [], messId, startDate, endDate, place.capacity)
    : [];

  const onSubmit = async (values: MessValues) => {
    setFormError(null);
    try {
      await create.mutateAsync({ body: { ...values, team_id: values.team_id || null }, idempotencyKey: idem.key });
      idem.renew();
      toast.success("Hunian mess berhasil dicatat.");
      onClose();
    } catch (err) {
      setFormError(applyFieldErrors(err, setError) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  };

  return (
    <VmsDialog dirty={isDirty}
      open
      title="Tempatkan Karyawan di Mess"
      onClose={onClose}
      footer={
        <DialogActions
          onCancel={onClose}
          busy={isSubmitting}
          formId="mess-form"
        />
      }
    >
      <FormBlock id="mess-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}

        <SelectField
          label="Karyawan yang Menempati"
          error={errors.employee_id?.message}
          {...register("employee_id")}
        >
          <ControlOption value="">-- Pilih Karyawan --</ControlOption>
          {employeeList.map((emp) => (
            <ControlOption key={emp.employee_id} value={emp.employee_id}>
              {emp.full_name} ({emp.employee_no || "Karyawan"})
            </ControlOption>
          ))}
        </SelectField>

        <SelectField
          label="Mess"
          error={errors.mess_id?.message}
          {...register("mess_id")}
        >
          <ControlOption value="">-- Pilih Mess --</ControlOption>
          {placeList.map((p) => (
            <ControlOption key={p.mess_id} value={p.mess_id}>
              {p.mess_name} · {p.city}
              {p.capacity ? ` (${p.occupied}/${p.capacity} terisi)` : ""}
            </ControlOption>
          ))}
        </SelectField>
        {places.isSuccess && placeList.length === 0 && (
          <TextBlock className="text-xs text-mist">
            Belum ada mess terdaftar. Tambahkan dulu di tab “Daftar Mess”.
          </TextBlock>
        )}

        <SelectField label="Tim yang menginap (opsional)" {...register("team_id")}>
          <ControlOption value="">Tanpa tim</ControlOption>
          {teams.data?.map((t) => (
            <ControlOption key={t.team_id} value={t.team_id}>{t.name}</ControlOption>
          ))}
        </SelectField>

        <div className="grid grid-cols-2 gap-2">
          <TextField
            label="Tanggal Mulai Inap"
            type="date"
            error={errors.stay_start_date?.message}
            {...register("stay_start_date")}
          />
          <TextField
            label="Tanggal Selesai Inap"
            type="date"
            error={errors.stay_end_date?.message}
            {...register("stay_end_date")}
          />
        </div>
        {fullDays.length > 0 && (
          <TextBlock role="alert" className="text-sm text-danger">
            Mess penuh pada {fullDays.map(dmy).join(", ")} (kapasitas {place?.capacity} orang). Pilih tanggal lain atau mess lain.
          </TextBlock>
        )}
      </FormBlock>
    </VmsDialog>
  );
}
