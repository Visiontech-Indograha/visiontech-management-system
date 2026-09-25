import { zodResolver } from "@hookform/resolvers/zod";
import { useState, type ReactNode } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { SelectField, TextAreaField, TextField } from "@/components/ui/Field";
import { Dialog } from "@/components/ui/VmsDialog";
import { errorMessage } from "@/lib/errors";
import {
  useActiveEmployees,
  useAddDay,
  useCreatePlan,
  useSetTeam,
  useSiteOptions,
  useTransition,
  useUpdatePlan,
  type Transition,
  type WorkPlan,
} from "./api";

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
    <Dialog
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
    </Dialog>
  );
}

const required = (msg: string) => z.string().trim().min(1, msg);
const period = <T extends { period_start: string; period_end: string }>(v: T) => v.period_end >= v.period_start;
const periodIssue = { path: ["period_end"], message: "Tanggal selesai tidak boleh sebelum tanggal mulai." };

const createSchema = z
  .object({
    title: required("Judul pekerjaan wajib diisi."),
    location_text: required("Lokasi wajib diisi."),
    description: z.string().trim(),
    period_start: required("Tanggal mulai wajib diisi."),
    period_end: required("Tanggal selesai wajib diisi."),
    pm_employee_id: required("Pilih PM pekerjaan."),
    leader_employee_id: z.string(),
    site_id: z.string(),
  })
  .refine(period, periodIssue);
type CreateValues = z.infer<typeof createSchema>;

/** Buat draft SK (POST /work-plans). Unit SK = unit karyawan PM yang dipilih. */
export function CreatePlanDialog({ onClose }: { onClose: () => void }) {
  const employees = useActiveEmployees();
  const sites = useSiteOptions();
  const create = useCreatePlan();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { title: "", location_text: "", description: "", period_start: "", period_end: "", pm_employee_id: "", leader_employee_id: "", site_id: "" },
  });

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    const unit_id = employees.data?.find((e) => e.id === v.pm_employee_id)?.unit_id;
    if (!unit_id) {
      setError("pm_employee_id", { message: "Karyawan ini belum terdaftar di unit bisnis mana pun." });
      return;
    }
    try {
      const plan = await create.mutateAsync({
        title: v.title,
        location_text: v.location_text,
        description: v.description || null,
        period_start: v.period_start,
        period_end: v.period_end,
        pm_employee_id: v.pm_employee_id,
        leader_employee_id: v.leader_employee_id || null,
        site_id: v.site_id || null,
        unit_id,
      });
      toast.success("Draft SK dibuat.");
      onClose();
      navigate(`/work-plans/${plan.id}`);
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });

  return (
    <FormDialog title="Buat SK" formId="create-plan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Judul pekerjaan" error={errors.title?.message} {...register("title")} />
      <TextField label="Lokasi" error={errors.location_text?.message} {...register("location_text")} />
      <SelectField label="Lokasi kerja (absensi)" {...register("site_id")}>
        <option value="">Tanpa lokasi kerja</option>
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
      <EmployeeSelect label="PM pekerjaan" error={errors.pm_employee_id?.message} emptyLabel="Pilih PM" {...register("pm_employee_id")} />
      <EmployeeSelect label="Ketua tim" emptyLabel="Tentukan nanti" {...register("leader_employee_id")} />
    </FormDialog>
  );
}

function EmployeeSelect({
  label,
  error,
  emptyLabel,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string; error?: string; emptyLabel: string } & {
  ref?: React.Ref<HTMLSelectElement>;
}) {
  const employees = useActiveEmployees();
  return (
    <SelectField label={label} error={error} hint={employees.isError ? "Daftar karyawan tidak dapat dimuat." : undefined} {...props}>
      <option value="">{employees.isPending ? "Memuat..." : emptyLabel}</option>
      {employees.data?.map((e) => (
        <option key={e.id} value={e.id}>
          {e.full_name} · {e.position}
        </option>
      ))}
    </SelectField>
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
  member_employee_ids: z.array(z.string()).min(1, "Pilih minimal satu anggota tim."),
});
type TeamValues = z.infer<typeof teamSchema>;

/** Tetapkan ketua & anggota (PUT /work-plans/{id}/members). API tidak mengirim daftar anggota saat ini. */
export function TeamDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const employees = useActiveEmployees();
  const setTeam = useSetTeam(plan.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<TeamValues>({
    resolver: zodResolver(teamSchema),
    defaultValues: { leader_employee_id: plan.leader_employee_id ?? "", member_employee_ids: [] },
  });
  const leader = useWatch({ control, name: "leader_employee_id" });
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
      <EmployeeSelect label="Ketua tim" emptyLabel="Pilih ketua" error={errors.leader_employee_id?.message} {...register("leader_employee_id")} />
      <fieldset className="mb-4">
        <legend className="mb-2 text-sm font-medium">Anggota tim</legend>
        <div className="max-h-56 space-y-1 overflow-y-auto rounded-control border border-line p-2">
          {employees.data
            ?.filter((e) => e.id !== leader)
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
  title: required("Judul hari wajib diisi."),
  tasks: z
    .array(z.object({ title: required("Tugas wajib diisi.") }))
    .min(1, "Isi minimal satu tugas.")
    .max(30, "Maksimal 30 tugas per hari."),
});
type DayValues = z.infer<typeof daySchema>;

/** Tambah rincian harian: POST /days lalu PUT /days/{day}/plan (judul + tugas). */
export function AddDayDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const addDay = useAddDay(plan.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<DayValues>({
    resolver: zodResolver(daySchema),
    defaultValues: { work_date: plan.period_start, title: "", tasks: [{ title: "" }] },
  });
  const tasks = useFieldArray({ control, name: "tasks" });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await addDay.mutateAsync({ work_date: v.work_date, title: v.title, tasks: v.tasks.map((t) => t.title) });
      toast.success("Rincian hari ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title="Tambah hari" formId="add-day" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Tanggal" type="date" min={plan.period_start} max={plan.period_end} error={errors.work_date?.message} {...register("work_date")} />
      <TextField label="Judul hari" error={errors.title?.message} {...register("title")} />
      {tasks.fields.map((f, i) => (
        <div key={f.id} className="flex items-end gap-2">
          <div className="flex-1">
            <TextField label={`Tugas ${i + 1}`} error={errors.tasks?.[i]?.title?.message} {...register(`tasks.${i}.title`)} />
          </div>
          {tasks.fields.length > 1 && (
            <Button type="button" variant="ghost" className="mb-4" onClick={() => tasks.remove(i)} aria-label={`Hapus tugas ${i + 1}`}>
              Hapus
            </Button>
          )}
        </div>
      ))}
      {errors.tasks?.root && <p className="mb-2 text-sm text-destructive">{errors.tasks.root.message}</p>}
      {tasks.fields.length < 30 && (
        <Button type="button" variant="outline" onClick={() => tasks.append({ title: "" })}>
          Tambah tugas
        </Button>
      )}
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
