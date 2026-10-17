import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { useCreateTeam } from "@/services/teamService";

const teamSchema = z.object({
  name: z.string().trim().min(1, "Nama tim wajib diisi."),
  leader_id: z.string().trim().min(1, "ID Ketua Tim wajib diisi."),
  description: z.string().trim().optional(),
});
type TeamValues = z.infer<typeof teamSchema>;

export function TeamFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateTeam();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<TeamValues>({
    resolver: zodResolver(teamSchema),
    defaultValues: { name: "", leader_id: "", description: "" },
  });

  const onSubmit = async (values: TeamValues) => {
    setFormError(null);
    try {
      await create.mutateAsync({
        name: values.name,
        leader_id: values.leader_id,
        description: values.description,
      });
      toast.success("Tim lapangan berhasil ditambahkan.");
      onClose();
    } catch {
      setFormError("Gagal menyimpan tim lapangan.");
    }
  };

  return (
    <VmsDialog
      open
      title="Tambah Tim Lapangan"
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={isSubmitting} formId="team-form" />}
    >
      <FormBlock id="team-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}
        <TextField
          label="Nama Tim"
          placeholder="Misal: Tim Alpha Fibre Optic"
          error={errors.name?.message}
          {...register("name")}
        />
        <TextField
          label="ID Ketua Tim (Leader)"
          placeholder="UUID Karyawan Ketua Tim"
          error={errors.leader_id?.message}
          {...register("leader_id")}
        />
        <TextField
          label="Keterangan / Wilayah Kerja"
          placeholder="Misal: Wilayah Rumbai - Duri"
          error={errors.description?.message}
          {...register("description")}
        />
      </FormBlock>
    </VmsDialog>
  );
}
