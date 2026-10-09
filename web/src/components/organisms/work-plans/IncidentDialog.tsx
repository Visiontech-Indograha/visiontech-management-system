import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import type { WorkPlan } from "@/services/workPlanService";
import { INCIDENT_CATEGORY, INCIDENT_SEVERITY, createIncident, useStoreIncident } from "@/services/incidentService";
import { oversize, uploadFiles } from "@/services/uploadService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";

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
      return createIncident({ work_plan_id: plan.id, ...v, evidence_file_ids });
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
        <FormErrorText message={formError} />
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
