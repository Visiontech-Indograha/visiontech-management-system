import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { TextField, SelectField, TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useCreateWorkCompletion } from "@/services/workCompletionService";

interface FormValues {
  client_name: string;
  project_title: string;
  order_number?: string;
  total_target_unit: number;
  unit_measure: string;
  priority_level: string;
  site_address?: string;
}

export function WorkCompletionFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateWorkCompletion();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    defaultValues: {
      client_name: "",
      project_title: "",
      order_number: "",
      total_target_unit: 1,
      unit_measure: "Titik / Unit",
      priority_level: "NORMAL",
      site_address: "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    try {
      await create.mutateAsync({
        client_name: values.client_name,
        project_title: values.project_title,
        order_number: values.order_number || undefined,
        total_target_unit: Number(values.total_target_unit),
        unit_measure: values.unit_measure,
        priority_level: values.priority_level,
        site_address: values.site_address || undefined,
      });
      toast.success("Order proyek klien berhasil dibuat.");
      onClose();
    } catch {
      setFormError("Gagal membuat order proyek klien. Pastikan input terisi dengan benar.");
    }
  };

  return (
    <VmsDialog
      open
      title="Buat Order Proyek Klien Baru"
      onClose={onClose}
    >
      <TextBlock className="mb-4 text-sm text-mist">
        Daftarkan entitas order pekerjaan klien (SPK/PO) untuk pembagian slot tugas tim lapangan.
      </TextBlock>
      <FormBlock id="work-completion-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}

        <TextField
          label="Nama Klien / Perusahaan"
          placeholder="misal: PT Pertamina EP, PT PLN Persero"
          error={errors.client_name?.message}
          {...register("client_name", { required: "Nama klien wajib diisi." })}
        />

        <TextField
          label="Judul Pekerjaan / Proyek"
          placeholder="misal: Pemasangan 13 Unit CCTV Kilang"
          error={errors.project_title?.message}
          {...register("project_title", { required: "Judul proyek wajib diisi." })}
        />

        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Nomor SPK / PO / WO (Opsional)"
            placeholder="misal: PO-2026-PTM-001"
            {...register("order_number")}
          />
          <SelectField
            label="Tingkat Prioritas"
            {...register("priority_level")}
          >
            <ControlOption value="NORMAL">Normal</ControlOption>
            <ControlOption value="HIGH">Tinggi (High)</ControlOption>
            <ControlOption value="URGENT">Mendesak (Urgent)</ControlOption>
            <ControlOption value="LOW">Rendah (Low)</ControlOption>
          </SelectField>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Total Target Unit / Volume"
            type="number"
            min={1}
            error={errors.total_target_unit?.message}
            {...register("total_target_unit", { valueAsNumber: true, min: 1 })}
          />
          <TextField
            label="Satuan Unit"
            placeholder="misal: Titik, Unit, Meter, Gardu"
            {...register("unit_measure")}
          />
        </div>

        <TextAreaField
          label="Alamat Site / Lokasi Pelaksanaan (Opsional)"
          placeholder="Alamat lengkap lokasi kerja proyek"
          rows={2}
          {...register("site_address")}
        />

        <DialogActions
          onCancel={onClose}
          busy={isSubmitting}
          formId="work-completion-form"
          submitLabel="Simpan Order"
          busyLabel="Menyimpan..."
        />
      </FormBlock>
    </VmsDialog>
  );
}
