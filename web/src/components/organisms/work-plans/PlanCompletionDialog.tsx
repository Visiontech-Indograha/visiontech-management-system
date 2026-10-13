import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useFormDraft } from "@/hooks/useFormDraft";
import { toast } from "sonner";
import { z } from "zod";
import { TextAreaField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { planKey, type WorkPlan, requestCompletion } from "@/services/workPlanService";
import { oversize, uploadFiles } from "@/services/uploadService";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { DialogActions } from "@/components/molecules/DialogActions";

type CompletionRequest = components["schemas"]["CompletionRequest"];

/** Unggah tiap berkas ke POST /files/upload, lalu POST request-completion dengan file_id-nya. */
function useRequestCompletion(plan: WorkPlan) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ body, obstacle, files }: { body: string; obstacle: string; files: File[] }) => {
      const evidence_file_ids = await uploadFiles(files);
      const payload: CompletionRequest = { row_version: plan.row_version, body, obstacle, evidence_file_ids };
      return requestCompletion(plan.id, payload);
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
export function PlanCompletionDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
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
    <VmsDialog
      open
      title="Laporan akhir"
      onClose={onClose}
      footer={
        <DialogActions onCancel={onClose} busy={isSubmitting} formId="completion-form" submitLabel="Kirim Laporan Akhir (Ajukan Selesai)" busyLabel="Mengirim..." />
      }
    >
      <FormBlock id="completion-form" onSubmit={onSubmit} noValidate className="max-h-[65vh] overflow-y-auto px-1">
        <FormErrorText message={formError} />
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
      </FormBlock>
    </VmsDialog>
  );
}
