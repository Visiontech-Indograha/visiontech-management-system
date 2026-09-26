import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useFormDraft } from "@/lib/drafts";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { TextAreaField, TextField } from "@/components/ui/Field";
import { Dialog } from "@/components/ui/VmsDialog";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { planKey, type WorkPlan } from "./api";
import { oversize, uploadFiles } from "./uploads";

type CompletionRequest = components["schemas"]["CompletionRequest"];

/** Unggah tiap berkas ke POST /files/upload, lalu POST request-completion dengan file_id-nya. */
function useRequestCompletion(plan: WorkPlan) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ body, obstacle, files }: { body: string; obstacle: string; files: File[] }) => {
      const evidence_file_ids = await uploadFiles(files);
      const payload: CompletionRequest = { row_version: plan.row_version, body, obstacle, evidence_file_ids };
      return (await api.post<WorkPlan>(`/work-plans/${plan.id}/request-completion`, payload)).data;
    },
    onSuccess: async (updated) => {
      qc.setQueryData(planKey(plan.id), updated);
      await qc.invalidateQueries({ queryKey: ["work-plans"] });
    },
  });
}

const schema = z.object({
  body: z.string().trim().min(1, "Laporan keseluruhan wajib diisi."),
  obstacle: z.string().trim().min(1, "Ringkasan kendala keseluruhan wajib diisi."),
});
type Values = z.infer<typeof schema>;

/** "Laporan Akhir Penyelesaian Pekerjaan" (prototype/js/workplans.js). Syarat penyelesaian diperiksa API. */
export function CompletionDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const request = useRequestCompletion(plan);
  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { body: "", obstacle: "" } });
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = form;
  // Dialog ditutup ("Batal") atau pindah layar → teks laporan akhir tetap ada saat dibuka lagi (R5).
  const dropDraft = useFormDraft(`completion:${plan.id}`, form);

  const pickFiles = (list: FileList | null) => {
    const picked = Array.from(list ?? []);
    const tooBig = oversize(picked);
    setFileError(tooBig);
    setFiles(tooBig ? [] : picked);
  };

  const onSubmit = handleSubmit(async (v) => {
    if (fileError) return;
    setFormError(null);
    try {
      await request.mutateAsync({ ...v, files });
      dropDraft();
      toast.success("Penyelesaian diajukan ke PM.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });

  return (
    <Dialog
      open
      title="Laporan akhir"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" form="completion-form" disabled={isSubmitting}>
            {isSubmitting ? "Mengirim..." : "Kirim Laporan Akhir (Ajukan Selesai)"}
          </Button>
        </>
      }
    >
      <form id="completion-form" onSubmit={onSubmit} noValidate className="max-h-[65vh] overflow-y-auto px-1">
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <TextAreaField label="Laporan Keseluruhan" error={errors.body?.message} {...register("body")} />
        <TextAreaField label="Ringkasan Kendala Keseluruhan (Wajib)" error={errors.obstacle?.message} {...register("obstacle")} />
        <TextField
          label="Lampiran (Foto/PDF) (Opsional)"
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.pdf"
          hint="Maksimal 10 MB per berkas."
          error={fileError ?? undefined}
          onChange={(e) => pickFiles(e.target.files)}
        />
      </form>
    </Dialog>
  );
}
