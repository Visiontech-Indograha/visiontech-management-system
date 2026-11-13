import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { DialogCancelButton } from "@/components/molecules/DialogActions";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { UploadField } from "@/components/molecules/UploadField";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { answerLabel, periodLabel } from "@/lib/inspectionLabels";
import { checklistBlocker, INSPECTION_MAX_NOTES, INSPECTION_MAX_PHOTOS, inspectionSchema, PERIOD_TYPES, type InspectionValues } from "@/schemas/inspectionSchemas";
import { useVehicles } from "@/services/assetService";
import { useChecklistTemplate, useCreateInspection } from "@/services/inspectionService";
import { oversize } from "@/services/uploadService";

const KNOWN = ["vehicle_id", "period_type", "odometer_km", "notes"] as const;

/** Buat inspeksi: pilih kendaraan dan jenis, jawab daftar periksa, tambah foto bukti (maks 10), lalu kirim. */
export function VehicleInspectionCreateDialog({ onClose }: { onClose: () => void }) {
  const template = useChecklistTemplate();
  const vehicles = useVehicles();
  const create = useCreateInspection();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [photos, setPhotos] = useState<File[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<InspectionValues>({
    resolver: zodResolver(inspectionSchema),
    defaultValues: { vehicle_id: "", period_type: "DAILY", odometer_km: "", notes: "" },
  });
  const items = template.data?.items ?? [];
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    const blocked = checklistBlocker(items.map((i) => i.key), answers, photos.length) ?? oversize(photos);
    if (blocked) return setFormError(blocked);
    try {
      await create.mutateAsync({
        body: {
          vehicle_id: v.vehicle_id,
          period_type: v.period_type,
          odometer_km: v.odometer_km ? Number(v.odometer_km) : null,
          checklist_json: answers,
          notes: v.notes || null,
        },
        photos,
      });
      toast.success("Inspeksi terkirim.");
      onClose();
    } catch (err) {
      setFormError(applyFieldErrors(err, setError, KNOWN) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  });
  return (
    <VmsDialog
      open
      title="Buat inspeksi kendaraan"
      onClose={onClose}
      footer={
        <>
          <DialogCancelButton onCancel={onClose} disabled={isSubmitting} />
          <ActionButton type="submit" form="inspection-form" disabled={isSubmitting || !template.data}>{isSubmitting ? "Mengirim..." : "Kirim inspeksi"}</ActionButton>
        </>
      }
    >
      <FormBlock id="inspection-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <SelectField label="Kendaraan" error={errors.vehicle_id?.message} {...register("vehicle_id")}>
          <ControlOption value="">Pilih kendaraan</ControlOption>
          {(vehicles.data ?? []).map((v) => <ControlOption key={v.vehicle_id} value={v.vehicle_id}>{v.number_plate} - {v.name}</ControlOption>)}
        </SelectField>
        <SelectField label="Jenis pemeriksaan" error={errors.period_type?.message} {...register("period_type")}>
          {PERIOD_TYPES.map((p) => <ControlOption key={p} value={p}>{periodLabel(p)}</ControlOption>)}
        </SelectField>
        <TextField label="Angka kilometer (boleh kosong)" inputMode="numeric" maxLength={8} error={errors.odometer_km?.message} {...register("odometer_km")} />
        <TextBlock className="mb-2 text-sm font-medium text-ink">Daftar periksa</TextBlock>
        <QueryState query={template} errorText="Daftar periksa belum bisa dimuat. Coba lagi." empty={items.length === 0} emptyText="Daftar periksa belum tersedia.">
          {items.map((item) => (
            <SelectField key={item.key} label={item.label} value={answers[item.key] ?? ""} onChange={(e) => setAnswers((a) => ({ ...a, [item.key]: e.target.value }))}>
              <ControlOption value="">Pilih kondisi</ControlOption>
              {item.options.map((o) => <ControlOption key={o} value={o}>{answerLabel(o)}</ControlOption>)}
            </SelectField>
          ))}
        </QueryState>
        <UploadField
          label="Foto bukti (boleh kosong)"
          accept=".jpg,.jpeg,.png"
          multiple
          hint={`Maksimal ${INSPECTION_MAX_PHOTOS} foto, tiap foto maksimal 10 MB. Dipilih: ${photos.length}.`}
          error={photos.length > INSPECTION_MAX_PHOTOS ? `Foto bukti maksimal ${INSPECTION_MAX_PHOTOS}.` : undefined}
          onChange={(e) => setPhotos(Array.from(e.target.files ?? []))}
        />
        <TextAreaField label="Catatan (boleh kosong)" maxLength={INSPECTION_MAX_NOTES} error={errors.notes?.message} {...register("notes")} />
      </FormBlock>
    </VmsDialog>
  );
}
