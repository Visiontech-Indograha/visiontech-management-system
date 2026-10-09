import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/app/session";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { api } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import type { WorkPlan } from "@/services/workPlanService";
import { INCIDENT_CATEGORY, INCIDENT_SEVERITY, key, useSessionIncidents, type Incident } from "@/services/incidentService";
import { oversize, uploadFiles } from "@/services/uploadService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";

function useStoreIncident(planId: string) {
  const qc = useQueryClient();
  return (inc: Incident) =>
    qc.setQueryData<Incident[]>(key(planId), (old = []) => [inc, ...old.filter((i) => i.id !== inc.id)]);
}

const schema = z.object({
  category: z.string().min(1, "Pilih kategori."),
  severity: z.string().min(1, "Pilih tingkat keparahan."),
  description: z.string().trim().min(1, "Uraian kejadian wajib diisi."),
});
type Values = z.infer<typeof schema>;

/** "Lapor Insiden/HSE" — ketua/anggota SK berjalan (POST /hse/incidents). */
export function IncidentDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const store = useStoreIncident(plan.id);
  const report = useMutation({
    mutationFn: async ({ files, ...v }: Values & { files: File[] }) => {
      const evidence_file_ids = await uploadFiles(files);
      return (await api.post<Incident>("/hse/incidents", { work_plan_id: plan.id, ...v, evidence_file_ids })).data;
    },
    onSuccess: store,
  });
  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { category: "", severity: "", description: "" } });

  const onSubmit = handleSubmit(async (v) => {
    if (fileError) return;
    setFormError(null);
    try {
      await report.mutateAsync({ ...v, files });
      toast.success("Insiden dilaporkan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });

  return (
    <VmsDialog
      open
      title="Lapor Insiden/HSE"
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="incident-form" variant="destructive" disabled={isSubmitting}>
            {isSubmitting ? "Mengirim..." : "Kirim laporan"}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="incident-form" onSubmit={onSubmit} noValidate className="max-h-[65vh] overflow-y-auto px-1">
        {formError && (
          <TextBlock role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </TextBlock>
        )}
        <SelectField label="Kategori" error={errors.category?.message} {...register("category")}>
          <ControlOption value="">Pilih kategori</ControlOption>
          {Object.entries(INCIDENT_CATEGORY).map(([v, l]) => (
            <ControlOption key={v} value={v}>
              {l}
            </ControlOption>
          ))}
        </SelectField>
        <SelectField label="Tingkat keparahan" error={errors.severity?.message} {...register("severity")}>
          <ControlOption value="">Pilih tingkat</ControlOption>
          {Object.entries(INCIDENT_SEVERITY).map(([v, l]) => (
            <ControlOption key={v} value={v}>
              {l}
            </ControlOption>
          ))}
        </SelectField>
        <TextAreaField label="Uraian kejadian" error={errors.description?.message} {...register("description")} />
        <TextField
          label="Bukti (Foto/PDF) (Opsional)"
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.pdf"
          hint="Maksimal 10 MB per berkas. Tanggal insiden dicatat server."
          error={fileError ?? undefined}
          onChange={(e) => {
            const picked = Array.from(e.target.files ?? []);
            const big = oversize(picked);
            setFileError(big);
            setFiles(big ? [] : picked);
          }}
        />
      </FormBlock>
    </VmsDialog>
  );
}

const resolveSchema = z.object({ resolution_note: z.string().trim().min(1, "Catatan penyelesaian wajib diisi.") });

/** "Laporan Insiden / HSE" di detail SK; PM (create:plan) atau petugas aset dapat menyelesaikan. */
export function IncidentPanel({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const canResolve = !!me && (me.permissions.includes("create:plan") || me.permissions.includes("manage:assets"));
  const incidents = useSessionIncidents(plan.id).data ?? [];
  const [resolving, setResolving] = useState<Incident | null>(null);
  if (incidents.length === 0) return null;
  return (
    <section aria-label="Laporan Insiden / HSE" className="rounded-panel border border-line bg-surface shadow-card p-4">
      <TextBlock as="h2" className="mb-3 text-base font-semibold">Laporan Insiden / HSE</TextBlock>
      <ListBlock className="space-y-3">
        {incidents.map((i) => (
          <ListEntry key={i.id} className="border-b border-line pb-3 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-2">
              <TextBlock as="strong" className="text-sm">
                [{INCIDENT_CATEGORY[i.category] ?? i.category}] {INCIDENT_SEVERITY[i.severity] ?? i.severity}
              </TextBlock>
              <StatusBadge status={i.status} />
            </div>
            <TextBlock className="text-sm">{i.description}</TextBlock>
            <TextBlock className="text-xs text-mist">{formatDate(i.occurred_on)}</TextBlock>
            {i.resolution_note && <TextBlock className="text-sm text-mist">Penyelesaian: {i.resolution_note}</TextBlock>}
            {canResolve && i.status !== "RESOLVED" && (
              <ActionButton size="sm" className="mt-2" onClick={() => setResolving(i)}>
                Selesaikan
              </ActionButton>
            )}
          </ListEntry>
        ))}
      </ListBlock>
      {resolving && <ResolveDialog plan={plan} incident={resolving} onClose={() => setResolving(null)} />}
    </section>
  );
}

function ResolveDialog({ plan, incident, onClose }: { plan: WorkPlan; incident: Incident; onClose: () => void }) {
  const store = useStoreIncident(plan.id);
  const resolve = useMutation({
    mutationFn: async (body: { resolution_note: string }) =>
      (await api.post<Incident>(`/hse/incidents/${incident.id}/resolve`, body)).data,
    onSuccess: store,
  });
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ resolution_note: string }>({ resolver: zodResolver(resolveSchema), defaultValues: { resolution_note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await resolve.mutateAsync(v);
      toast.success("Insiden diselesaikan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <VmsDialog
      open
      title="Selesaikan insiden"
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="resolve-form" disabled={isSubmitting}>
            Selesaikan
          </ActionButton>
        </>
      }
    >
      <FormBlock id="resolve-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <TextBlock role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </TextBlock>
        )}
        <TextAreaField label="Catatan penyelesaian" error={errors.resolution_note?.message} {...register("resolution_note")} />
      </FormBlock>
    </VmsDialog>
  );
}
