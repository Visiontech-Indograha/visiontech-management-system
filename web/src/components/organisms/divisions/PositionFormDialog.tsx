import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { DialogActions } from "@/components/molecules/DialogActions";
import { TextField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { positionSchema, type PositionValues } from "@/schemas/divisionAdminSchemas";
import { useSavePosition, type PositionRow } from "@/services/divisionAdminService";

const KNOWN = ["code", "name", "grade_level"] as const;

/** Dialog tambah/ubah jabatan. `divisionId` = divisi tempat jabatan baru ditambahkan (kosong = jabatan umum). */
export function PositionFormDialog({ position, divisionId, onClose }: {
  position: PositionRow | null;
  divisionId: string | null;
  onClose: () => void;
}) {
  const save = useSavePosition(position?.position_id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<PositionValues>({
    resolver: zodResolver(positionSchema),
    defaultValues: { code: position?.code ?? "", name: position?.name ?? "", grade_level: position?.grade_level ?? 1 },
  });

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      const body = { code: v.code.trim(), name: v.name.trim(), grade_level: v.grade_level };
      await save.mutateAsync(position ? body : { ...body, division_id: divisionId });
      toast.success(position ? "Jabatan disimpan." : "Jabatan ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(applyFieldErrors(err, setError, KNOWN) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  });

  return (
    <VmsDialog
      open
      dirty={isDirty}
      title={position ? "Ubah jabatan" : "Tambah jabatan"}
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={isSubmitting} formId="position-form" />}
    >
      <FormBlock id="position-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <TextField label="Kode jabatan" maxLength={30} error={errors.code?.message} {...register("code")} />
        <TextField label="Nama jabatan" maxLength={100} error={errors.name?.message} {...register("name")} />
        <TextField
          label="Tingkat"
          type="number"
          min={1}
          max={20}
          hint="Angka 1 sampai 20. Semakin besar, semakin tinggi jabatannya."
          error={errors.grade_level?.message}
          {...register("grade_level", { valueAsNumber: true })}
        />
      </FormBlock>
    </VmsDialog>
  );
}
