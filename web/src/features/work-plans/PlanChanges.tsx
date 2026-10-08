import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/app/session";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/ui/button";
import { SelectField, TextAreaField, TextField } from "@/components/ui/Field";
import { Dialog } from "@/components/ui/VmsDialog";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { planKey, useActiveEmployees, type WorkPlan } from "./api";

type Change = components["schemas"]["ChangeResponse"];
type ChangeRequest = components["schemas"]["ChangeRequest"];
type Decision = "approve" | "accept" | "reject" | "withdraw";

/**
 * API belum punya endpoint baca usulan perubahan. Usulan yang baru diajukan disimpan di cache
 * query (hasil respons API, bukan data buatan) agar keputusan lanjutannya bisa diambil di sesi ini.
 */
const changeKey = (planId: string) => ["plan-change", planId] as const;
const useLastChange = (planId: string) =>
  useQuery<Change | null>({ queryKey: changeKey(planId), queryFn: () => null, staleTime: Infinity, gcTime: Infinity });

function useChangeMutation<V>(planId: string, fn: (v: V) => Promise<Change>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async (change) => {
      qc.setQueryData(changeKey(planId), change);
      await qc.invalidateQueries({ queryKey: planKey(planId) });
    },
  });
}

const useRequestChange = (planId: string) =>
  useChangeMutation(planId, async (body: ChangeRequest) => (await api.post<Change>(`/work-plans/${planId}/changes`, body)).data);

function FormShell({
  title,
  submitLabel,
  submitting,
  formError,
  onClose,
  onSubmit,
  children,
}: {
  title: string;
  submitLabel: string;
  submitting: boolean;
  formError: string | null;
  onClose: () => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  children: React.ReactNode;
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
          <Button type="submit" form="change-form" disabled={submitting}>
            {submitting ? "Mengirim..." : submitLabel}
          </Button>
        </>
      }
    >
      <form id="change-form" onSubmit={onSubmit} noValidate className="max-h-[65vh] overflow-y-auto px-1">
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

/** Ketua mengajukan perpanjangan (ChangeRequest type EXTEND). */
export function ExtensionDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const request = useRequestChange(plan.id);
  const [formError, setFormError] = useState<string | null>(null);
  const schema = z.object({
    new_period_end: z
      .string()
      .min(1, "Tanggal akhir baru wajib diisi.")
      .refine((v) => v > plan.period_end, { message: "Tanggal akhir baru harus setelah akhir rencana saat ini." }),
    reason: z.string().trim().min(1, "Alasan perpanjangan wajib diisi."),
  });
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { new_period_end: "", reason: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await request.mutateAsync({ type: "EXTEND", ...v });
      toast.success("Perpanjangan diajukan ke PM.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormShell title="Ajukan perpanjangan" submitLabel="Ajukan perpanjangan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Tanggal akhir baru" type="date" min={plan.period_end} error={errors.new_period_end?.message} {...register("new_period_end")} />
      <TextAreaField label="Alasan" error={errors.reason?.message} {...register("reason")} />
    </FormShell>
  );
}

const personnelSchema = z.object({
  leader_employee_id: z.string().min(1, "Pilih ketua tim."),
  member_employee_ids: z.array(z.string()).min(1, "Pilih minimal satu anggota tim."),
  reason: z.string().trim().min(1, "Alasan revisi wajib diisi."),
});
type PersonnelValues = z.infer<typeof personnelSchema>;

/** PM mengajukan adendum personel (ChangeRequest type PERSONNEL). */
export function PersonnelDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const employees = useActiveEmployees();
  const request = useRequestChange(plan.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PersonnelValues>({
    resolver: zodResolver(personnelSchema),
    defaultValues: { leader_employee_id: plan.leader_employee_id ?? "", member_employee_ids: [], reason: "" },
  });
  const leader = useWatch({ control, name: "leader_employee_id" });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await request.mutateAsync({
        type: "PERSONNEL",
        reason: v.reason,
        leader_employee_id: v.leader_employee_id,
        member_employee_ids: v.member_employee_ids.filter((id) => id !== v.leader_employee_id),
      });
      toast.success("Revisi personel diajukan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormShell title="Revisi personel" submitLabel="Ajukan revisi" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Ketua tim" error={errors.leader_employee_id?.message} {...register("leader_employee_id")}>
        <option value="">{employees.isPending ? "Memuat..." : "Pilih ketua"}</option>
        {employees.data?.map((e) => (
          <option key={e.id} value={e.id}>
            {e.full_name} · {e.position}
          </option>
        ))}
      </SelectField>
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
      <TextAreaField label="Alasan" error={errors.reason?.message} {...register("reason")} />
    </FormShell>
  );
}

const TYPE_LABEL: Record<string, string> = { EXTEND: "Perpanjangan", PERSONNEL: "Revisi personel" };
const OPEN = ["PENDING_PM", "AWAITING_LEADER_ACCEPTANCE"];

/** Keputusan atas usulan terakhir: approve/reject (PM), accept/reject (ketua), withdraw (PM, personel). */
export function ChangePanel({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const canManage = !!me?.permissions.includes("create:plan");
  const change = useLastChange(plan.id).data;
  const decide = useChangeMutation(plan.id, async ({ action, reason }: { action: Decision; reason?: string }) =>
    (await api.post<Change>(`/changes/${change?.id}/${action}`, { reason: reason ?? null })).data,
  );
  const [asking, setAsking] = useState<{ action: Decision; title: string } | null>(null);
  if (!change) return null;

  const run = async (action: Decision, done: string, reason?: string) => {
    try {
      await decide.mutateAsync({ action, reason });
      toast.success(done);
      setAsking(null);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  const open = OPEN.includes(change.status);
  const buttons: React.ReactNode[] = [];
  if (open && change.status === "PENDING_PM" && canManage)
    buttons.push(
      <Button key="approve" onClick={() => run("approve", "Perpanjangan disetujui.")} disabled={decide.isPending}>
        Setujui perpanjangan
      </Button>,
      <Button key="reject-pm" variant="outline" onClick={() => setAsking({ action: "reject", title: "Tolak perpanjangan" })}>
        Tolak perpanjangan
      </Button>,
    );
  if (change.status === "AWAITING_LEADER_ACCEPTANCE") {
    buttons.push(
      <Button key="accept" onClick={() => run("accept", "Revisi diterima.")} disabled={decide.isPending}>
        Terima revisi
      </Button>,
      <Button key="reject-leader" variant="outline" onClick={() => setAsking({ action: "reject", title: "Tolak permintaan" })}>
        Tolak permintaan
      </Button>,
    );
    if (canManage && change.change_type === "PERSONNEL")
      buttons.push(
        <Button key="withdraw" variant="outline" onClick={() => setAsking({ action: "withdraw", title: "Tarik revisi personel" })}>
          Tarik revisi personel
        </Button>,
      );
  }

  return (
    <section aria-label="Usulan perubahan" className="rounded-panel border border-line bg-surface shadow-card p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold">{TYPE_LABEL[change.change_type] ?? change.change_type}</h2>
        <StatusBadge status={change.status} />
      </div>
      <p className="mb-3 text-sm">{change.reason}</p>
      {change.decision_reason && <p className="mb-3 text-sm text-mist">Catatan: {change.decision_reason}</p>}
      <div className="flex flex-col gap-2 [&>button]:w-full">{buttons}</div>
      {asking && <DecisionReasonDialog title={asking.title} onClose={() => setAsking(null)} onSubmit={(r) => run(asking.action, `${asking.title} berhasil.`, r)} />}
    </section>
  );
}

const reasonSchema = z.object({ reason: z.string().trim().min(1, "Alasan wajib diisi.") });

function DecisionReasonDialog({ title, onClose, onSubmit }: { title: string; onClose: () => void; onSubmit: (reason: string) => Promise<void> }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ reason: string }>({ resolver: zodResolver(reasonSchema), defaultValues: { reason: "" } });
  return (
    <FormShell title={title} submitLabel={title} submitting={isSubmitting} formError={null} onClose={onClose} onSubmit={handleSubmit(({ reason }) => onSubmit(reason))}>
      <TextAreaField label="Alasan" error={errors.reason?.message} {...register("reason")} />
    </FormShell>
  );
}
