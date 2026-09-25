import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
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
import { formatDate } from "@/lib/format";
import type { WorkPlan } from "./api";
import { oversize, uploadFiles } from "./uploads";

type Incident = components["schemas"]["IncidentResponse"];

const INCIDENT_CATEGORY: Record<string, string> = {
  K3_RINGAN: "K3 ringan",
  K3_BERAT: "K3 berat",
  K3_LINGKUNGAN: "K3 lingkungan",
  K3_HAMPIR: "Hampir celaka",
  ASET: "Aset",
};
const INCIDENT_SEVERITY: Record<string, string> = { RENDAH: "Rendah", SEDANG: "Sedang", TINGGI: "Tinggi", KRITIS: "Kritis" };

/**
 * API belum punya GET insiden per SK. Insiden yang dilaporkan/diselesaikan di sesi ini disimpan
 * di cache query dari respons API agar bisa ditindaklanjuti; setelah muat ulang daftar kosong.
 */
const key = (planId: string) => ["incidents", planId] as const;
const useSessionIncidents = (planId: string) =>
  useQuery<Incident[]>({ queryKey: key(planId), queryFn: () => [], staleTime: Infinity, gcTime: Infinity });

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
    <Dialog
      open
      title="Lapor Insiden/HSE"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" form="incident-form" variant="destructive" disabled={isSubmitting}>
            {isSubmitting ? "Mengirim..." : "Kirim laporan"}
          </Button>
        </>
      }
    >
      <form id="incident-form" onSubmit={onSubmit} noValidate className="max-h-[65vh] overflow-y-auto px-1">
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <SelectField label="Kategori" error={errors.category?.message} {...register("category")}>
          <option value="">Pilih kategori</option>
          {Object.entries(INCIDENT_CATEGORY).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </SelectField>
        <SelectField label="Tingkat keparahan" error={errors.severity?.message} {...register("severity")}>
          <option value="">Pilih tingkat</option>
          {Object.entries(INCIDENT_SEVERITY).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
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
      </form>
    </Dialog>
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
    <section aria-label="Laporan Insiden / HSE" className="rounded-panel border border-line bg-surface p-4">
      <h2 className="mb-3 text-base font-semibold">Laporan Insiden / HSE</h2>
      <ul className="space-y-3">
        {incidents.map((i) => (
          <li key={i.id} className="border-b border-line pb-3 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-2">
              <strong className="text-sm">
                [{INCIDENT_CATEGORY[i.category] ?? i.category}] {INCIDENT_SEVERITY[i.severity] ?? i.severity}
              </strong>
              <StatusBadge status={i.status} />
            </div>
            <p className="text-sm">{i.description}</p>
            <p className="text-xs text-mist">{formatDate(i.occurred_on)}</p>
            {i.resolution_note && <p className="text-sm text-mist">Penyelesaian: {i.resolution_note}</p>}
            {canResolve && i.status !== "RESOLVED" && (
              <Button size="sm" className="mt-2" onClick={() => setResolving(i)}>
                Selesaikan
              </Button>
            )}
          </li>
        ))}
      </ul>
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
    <Dialog
      open
      title="Selesaikan insiden"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" form="resolve-form" disabled={isSubmitting}>
            Selesaikan
          </Button>
        </>
      }
    >
      <form id="resolve-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <TextAreaField label="Catatan penyelesaian" error={errors.resolution_note?.message} {...register("resolution_note")} />
      </form>
    </Dialog>
  );
}
