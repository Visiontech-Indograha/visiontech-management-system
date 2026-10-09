import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState, type ReactNode } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/atoms/Button";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import {
  useAddDay,
  useAssignmentOptions,
  useAvailableVehicles,
  useCreatePlanWithTeam,
  useSetTeam,
  useSiteOptions,
  useTransition,
  useUpdatePlan,
  type Transition,
  type WorkPlan,
} from "./api";
import { usePlanTeam } from "./report-api";

function FormDialog({
  title,
  formId,
  submitting,
  submitLabel = "Simpan",
  formError,
  onClose,
  onSubmit,
  children,
}: {
  title: string;
  formId: string;
  submitting: boolean;
  submitLabel?: string;
  formError: string | null;
  onClose: () => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}) {
  return (
    <VmsDialog
      open
      title={title}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Batal
          </Button>
          <Button type="submit" form={formId} disabled={submitting}>
            {submitting ? "Menyimpan..." : submitLabel}
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={onSubmit} noValidate className="max-h-[65vh] overflow-y-auto px-1">
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        {children}
      </form>
    </VmsDialog>
  );
}

const required = (msg: string) => z.string().trim().min(1, msg);
const period = <T extends { period_start: string; period_end: string }>(v: T) => v.period_end >= v.period_start;
const periodIssue = { path: ["period_end"], message: "Tanggal selesai tidak boleh sebelum tanggal mulai." };

const createSchema = z
  .object({
    title: required("Judul pekerjaan wajib diisi."),
    description: z.string().trim(),
    period_start: required("Tanggal mulai wajib diisi."),
    period_end: required("Tanggal selesai wajib diisi."),
    pm_employee_id: z.string(),
    leader_employee_id: required("Pilih ketua tim."),
    member_employee_ids: z.array(z.string()),
    site_id: required("Pilih lokasi pekerjaan."),
    vehicle_id: z.string(),
    driver_employee_id: z.string(),
  })
  .refine(period, periodIssue)
  .refine((value) => !value.vehicle_id || value.driver_employee_id.length > 0, {
    path: ["driver_employee_id"],
    message: "Pilih pengemudi kendaraan.",
  });
type CreateValues = z.infer<typeof createSchema>;

/** Buat draft SK (POST /work-plans). Unit SK = unit karyawan PM yang dipilih. */
export function CreatePlanDialog({ onClose }: { onClose: () => void }) {
  const sites = useSiteOptions();
  const vehicles = useAvailableVehicles();
  const create = useCreatePlanWithTeam();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      title: "",
      description: "",
      period_start: "",
      period_end: "",
      pm_employee_id: "",
      leader_employee_id: "",
      member_employee_ids: [],
      site_id: "",
      vehicle_id: "",
      driver_employee_id: "",
    },
  });
  const periodStart = useWatch({ control, name: "period_start" });
  const periodEnd = useWatch({ control, name: "period_end" });
  const selectedPm = useWatch({ control, name: "pm_employee_id" });
  const selectedLeader = useWatch({ control, name: "leader_employee_id" });
  const selectedVehicle = useWatch({ control, name: "vehicle_id" });
  const selectedMembers = useWatch({ control, name: "member_employee_ids" });
  const options = useAssignmentOptions(periodStart, periodEnd);
  const effectivePm = selectedPm || options.data?.fixed_pm_employee_id;

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    const pm_employee_id = options.data?.can_choose_pm ? v.pm_employee_id : options.data?.fixed_pm_employee_id;
    const unit_id = options.data?.can_choose_pm
      ? options.data.pm_options.find((employee) => employee.id === pm_employee_id)?.unit_id
      : options.data?.fixed_unit_id;
    const location = sites.data?.find((site) => site.id === v.site_id);
    if (!pm_employee_id || !unit_id || !location) return setFormError("Pilihan PM atau lokasi belum lengkap.");
    try {
      const plan = await create.mutateAsync({
        plan: {
          title: v.title,
          location_text: location.name,
          description: v.description || null,
          period_start: v.period_start,
          period_end: v.period_end,
          pm_employee_id,
          leader_employee_id: v.leader_employee_id,
          site_id: v.site_id,
          unit_id,
        },
        leader_employee_id: v.leader_employee_id,
        member_employee_ids: v.member_employee_ids.filter((id) => id !== v.leader_employee_id),
        vehicle_id: v.vehicle_id || undefined,
        driver_employee_id: v.driver_employee_id || undefined,
      });
      toast.success("Draft rencana kerja dan tim berhasil dibuat.");
      onClose();
      navigate(`/work-plans/${plan.id}`);
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });

  return (
    <FormDialog title="Buat rencana kerja" formId="create-plan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Judul pekerjaan" error={errors.title?.message} {...register("title")} />
      <SelectField label="Lokasi pekerjaan" error={errors.site_id?.message} {...register("site_id")}>
        <option value="">Pilih lokasi</option>
        {sites.data?.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </SelectField>
      <TextAreaField label="Uraian" error={errors.description?.message} {...register("description")} />
      <div className="grid gap-x-3 md:grid-cols-2">
        <TextField label="Tanggal mulai" type="date" error={errors.period_start?.message} {...register("period_start")} />
        <TextField label="Tanggal selesai" type="date" error={errors.period_end?.message} {...register("period_end")} />
      </div>
      {options.data?.can_choose_pm ? (
        <SelectField label="PM pekerjaan" error={errors.pm_employee_id?.message} {...register("pm_employee_id")}>
          <option value="">Pilih PM</option>
          {options.data.pm_options.map((employee) => (
            <option key={employee.id} value={employee.id}>{employee.full_name} · {employee.position}</option>
          ))}
        </SelectField>
      ) : (
        <p className="mb-4 rounded-control bg-canvas px-3 py-2 text-sm text-mist">PM pekerjaan otomatis adalah Anda.</p>
      )}
      <SelectField label="Ketua tim" error={errors.leader_employee_id?.message} {...register("leader_employee_id")}>
        <option value="">{options.isPending ? "Memuat..." : "Pilih ketua"}</option>
        {options.data?.personnel_options.filter((employee) => employee.id !== effectivePm).map((employee) => (
          <option key={employee.id} value={employee.id}>{employee.full_name} · {employee.position}</option>
        ))}
      </SelectField>
      <fieldset className="mb-4">
        <legend className="mb-2 text-sm font-medium">Anggota tim</legend>
        <div className="max-h-48 space-y-1 overflow-y-auto rounded-control border border-line p-2">
          {options.data?.personnel_options
            .filter((employee) => employee.id !== effectivePm && employee.id !== selectedLeader)
            .map((employee) => (
              <label key={employee.id} className="flex min-h-11 items-center gap-2 text-sm">
                <input type="checkbox" className="size-5" value={employee.id} {...register("member_employee_ids")} />
                {employee.full_name} · {employee.position}
              </label>
            ))}
        </div>
        {errors.member_employee_ids && <p className="mt-1 text-sm text-destructive">{errors.member_employee_ids.message}</p>}
      </fieldset>
      <SelectField
        label="Kendaraan (opsional)"
        hint={vehicles.isError ? "Daftar kendaraan tidak dapat dimuat." : "Hanya kendaraan berstatus tersedia dan belum terikat rencana kerja."}
        {...register("vehicle_id")}
      >
        <option value="">Tanpa kendaraan</option>
        {vehicles.data?.map((vehicle) => (
          <option key={vehicle.id} value={vehicle.id}>{vehicle.name} · {vehicle.code}</option>
        ))}
      </SelectField>
      {selectedVehicle && (
        <SelectField label="Pengemudi kendaraan" error={errors.driver_employee_id?.message} {...register("driver_employee_id")}>
          <option value="">Pilih pengemudi</option>
          {options.data?.personnel_options
            .filter((employee) => employee.id === selectedLeader || selectedMembers.includes(employee.id))
            .map((employee) => <option key={employee.id} value={employee.id}>{employee.full_name}</option>)}
        </SelectField>
      )}
    </FormDialog>
  );
}

const editSchema = z
  .object({
    title: required("Judul pekerjaan wajib diisi."),
    location_text: required("Lokasi wajib diisi."),
    description: z.string().trim(),
    period_start: required("Tanggal mulai wajib diisi."),
    period_end: required("Tanggal selesai wajib diisi."),
  })
  .refine(period, periodIssue);
type EditValues = z.infer<typeof editSchema>;

/** Sunting draft (PATCH /work-plans/{id}, optimistic lock row_version). */
export function EditDraftDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const update = useUpdatePlan(plan.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      title: plan.title,
      location_text: plan.location_text,
      description: plan.description ?? "",
      period_start: plan.period_start,
      period_end: plan.period_end,
    },
  });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await update.mutateAsync({ ...v, description: v.description || null, row_version: plan.row_version });
      toast.success("Draft disimpan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title="Sunting draft" formId="edit-plan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Judul pekerjaan" error={errors.title?.message} {...register("title")} />
      <TextField label="Lokasi" error={errors.location_text?.message} {...register("location_text")} />
      <TextAreaField label="Uraian" {...register("description")} />
      <div className="grid gap-x-3 md:grid-cols-2">
        <TextField label="Tanggal mulai" type="date" error={errors.period_start?.message} {...register("period_start")} />
        <TextField label="Tanggal selesai" type="date" error={errors.period_end?.message} {...register("period_end")} />
      </div>
    </FormDialog>
  );
}

const teamSchema = z.object({
  leader_employee_id: required("Pilih ketua tim."),
  member_employee_ids: z.array(z.string()),
});
type TeamValues = z.infer<typeof teamSchema>;

/** Tetapkan ketua & anggota (PUT /work-plans/{id}/members). Dialog dibuka dengan tim saat ini
 * (GET /members); anggota yang sudah ada tetap tampil walau tidak ada di pilihan PM, misalnya personel
 * lintas unit pilihan OPS (R-26), agar tidak terhapus diam-diam saat disimpan. */
export function TeamDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const options = useAssignmentOptions(plan.period_start, plan.period_end);
  const team = usePlanTeam(plan.id);
  const setTeam = useSetTeam(plan.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<TeamValues>({
    resolver: zodResolver(teamSchema),
    defaultValues: { leader_employee_id: plan.leader_employee_id ?? "", member_employee_ids: [] },
  });
  const leader = useWatch({ control, name: "leader_employee_id" });
  const ready = !options.isPending && !team.isPending;
  useEffect(() => {
    if (!ready || isDirty || !team.data) return;
    reset({
      leader_employee_id: team.data.find((m) => m.role_in_plan === "LEADER")?.employee_id ?? plan.leader_employee_id ?? "",
      member_employee_ids: team.data.filter((m) => m.role_in_plan === "MEMBER").map((m) => m.employee_id),
    });
  }, [ready, isDirty, team.data, reset, plan.leader_employee_id]);
  const offered = options.data?.personnel_options ?? [];
  const people = [
    ...offered,
    ...(team.data ?? [])
      .filter((m) => !offered.some((o) => o.id === m.employee_id))
      .map((m) => ({ id: m.employee_id, full_name: m.full_name, position: m.position })),
  ];
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await setTeam.mutateAsync({
        leader_employee_id: v.leader_employee_id,
        member_employee_ids: v.member_employee_ids.filter((id) => id !== v.leader_employee_id),
        row_version: plan.row_version,
      });
      toast.success("Tim disimpan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title="Atur tim" formId="team" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Ketua tim" error={errors.leader_employee_id?.message} {...register("leader_employee_id")}>
        <option value="">{ready ? "Pilih ketua" : "Memuat..."}</option>
        {people
          .filter((employee) => employee.id !== plan.pm_employee_id)
          .map((employee) => <option key={employee.id} value={employee.id}>{employee.full_name} · {employee.position}</option>)}
      </SelectField>
      <fieldset className="mb-4">
        <legend className="mb-2 text-sm font-medium">Anggota tim</legend>
        <div className="max-h-56 space-y-1 overflow-y-auto rounded-control border border-line p-2">
          {people
            .filter((e) => e.id !== leader && e.id !== plan.pm_employee_id)
            .map((e) => (
              <label key={e.id} className="flex min-h-11 items-center gap-2 text-sm">
                <input type="checkbox" className="size-5" value={e.id} {...register("member_employee_ids")} />
                {e.full_name} · {e.position}
              </label>
            ))}
        </div>
        {errors.member_employee_ids && (
          <p role="alert" className="mt-1 text-sm text-destructive">
            {errors.member_employee_ids.message}
          </p>
        )}
      </fieldset>
    </FormDialog>
  );
}

const daySchema = z.object({
  work_date: required("Tanggal wajib diisi."),
  title: required("Nama pekerjaan wajib diisi."),
  description: required("Deskripsi pekerjaan wajib diisi."),
});
type DayValues = z.infer<typeof daySchema>;

/** Tambah rincian harian: POST /days lalu PUT /days/{day}/plan (judul + tugas). */
export function AddDayDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const addDay = useAddDay(plan.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<DayValues>({
    resolver: zodResolver(daySchema),
    defaultValues: { work_date: plan.period_start, title: "", description: "" },
  });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await addDay.mutateAsync({ work_date: v.work_date, title: v.title, tasks: [v.description] });
      toast.success("Rincian hari ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title="Tambah hari" formId="add-day" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Tanggal" type="date" min={plan.period_start} max={plan.period_end} error={errors.work_date?.message} {...register("work_date")} />
      <TextField label="Nama pekerjaan" error={errors.title?.message} {...register("title")} />
      <TextAreaField label="Deskripsi pekerjaan" error={errors.description?.message} {...register("description")} />
    </FormDialog>
  );
}

const reasonSchema = z.object({ reason: required("Alasan wajib diisi.") });

/** Dialog alasan untuk banding, batal, arsip (TransitionRequest.reason). */
export function ReasonDialog({
  plan,
  action,
  title,
  label,
  onClose,
}: {
  plan: WorkPlan;
  action: Transition;
  title: string;
  label: string;
  onClose: () => void;
}) {
  const transition = useTransition(plan.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ reason: string }>({ resolver: zodResolver(reasonSchema), defaultValues: { reason: "" } });
  const onSubmit = handleSubmit(async ({ reason }) => {
    setFormError(null);
    try {
      await transition.mutateAsync({ action, row_version: plan.row_version, reason });
      toast.success(`${title} berhasil.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title={title} formId="reason" submitting={isSubmitting} submitLabel={title} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextAreaField label={label} error={errors.reason?.message} {...register("reason")} />
    </FormDialog>
  );
}
