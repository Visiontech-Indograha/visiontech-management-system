import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { FilePreview } from "@/components/molecules/FilePreview";
import { QueryState } from "@/components/molecules/QueryState";
import { Button } from "@/components/atoms/Button";
import { TextField } from "@/components/molecules/Field";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import type { WorkPlan } from "../workPlanService";
import { oversize, uploadFiles } from "../uploadService";

type Attachment = components["schemas"]["AttachmentResponse"];
const key = (planId: string) => ["plan-attachments", planId] as const;

function formatSize(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/**
 * Lampiran SK (GET/PUT /work-plans/{id}/attachments, V-29). Semua yang melihat SK dapat membaca;
 * PM (create:plan) menambah/menghapus selagi DRAFT — PUT mengganti seluruh daftar. Saat terbit dibekukan.
 */
export function PlanAttachmentsPanel({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const editable = plan.status === "DRAFT" && !!me?.permissions.includes("create:plan");
  const qc = useQueryClient();
  const list = useQuery({
    queryKey: key(plan.id),
    queryFn: async () => (await api.get<Attachment[]>(`/work-plans/${plan.id}/attachments`)).data,
  });
  const save = useMutation({
    mutationFn: async (file_ids: string[]) =>
      (
        await api.put<Attachment[]>(`/work-plans/${plan.id}/attachments`, {
          file_ids,
        })
      ).data,
    onSuccess: (data) => qc.setQueryData(key(plan.id), data),
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const current = list.data ?? [];

  const run = async (next: () => Promise<string[]>, done: string) => {
    setError(null);
    setBusy(true);
    try {
      await save.mutateAsync(await next());
      toast.success(done);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const add = (files: FileList | null) => {
    const picked = files ? Array.from(files) : [];
    if (picked.length === 0) return;
    const tooBig = oversize(picked);
    if (tooBig) return setError(tooBig);
    void run(async () => [...current.map((a) => a.file_id), ...(await uploadFiles(picked))], "Lampiran ditambahkan.");
  };
  const remove = (id: string) => run(async () => current.filter((a) => a.file_id !== id).map((a) => a.file_id), "Lampiran dihapus.");

  if (!editable && list.isSuccess && current.length === 0) return null;

  return (
    <section aria-label="Lampiran rencana kerja" className="mt-6 rounded-panel border border-line bg-surface shadow-card p-4">
      <h2 className="mb-3 text-base font-semibold">Lampiran</h2>
      {error && (
        <p role="alert" className="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}
      <QueryState query={list} errorText="Lampiran tidak dapat dimuat." empty={current.length === 0} emptyText="Belum ada lampiran.">
        <ul className="space-y-3">
          {current.map((a) => (
            <li key={a.file_id} className="flex flex-wrap items-center gap-3">
              <FilePreview fileId={a.file_id} fileName={a.file_name} />
              <div className="min-w-0 flex-1 text-sm">
                <p className="truncate font-medium">{a.file_name}</p>
                <p className="text-mist">{formatSize(a.byte_size)}</p>
              </div>
              {editable && (
                <Button variant="outline" onClick={() => remove(a.file_id)} disabled={busy} aria-label={`Hapus ${a.file_name}`}>
                  Hapus
                </Button>
              )}
            </li>
          ))}
        </ul>
      </QueryState>
      {editable && (
        <div className="mt-4">
          <TextField
            label="Tambah lampiran (Foto/PDF)"
            type="file"
            multiple
            accept=".jpg,.jpeg,.png,.pdf"
            hint="Maksimal 10 MB per berkas. Lampiran dibekukan saat rencana kerja diterbitkan."
            disabled={busy}
            onChange={(e) => {
              add(e.target.files);
              e.target.value = "";
            }}
          />
        </div>
      )}
    </section>
  );
}
