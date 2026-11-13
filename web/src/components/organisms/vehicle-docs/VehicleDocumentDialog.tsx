import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { UploadField } from "@/components/molecules/UploadField";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { DocFormDialog } from "./DocFormDialog";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { vehicleDocumentSchema, type VehicleDocumentValues } from "@/schemas/vehicleDocumentSchemas";
import { useUploadFile } from "@/services/employeeService";
import { oversize } from "@/services/uploadService";
import { useAddVehicleDocument, useDocumentTypes } from "@/services/vehicleDocumentService";

const KNOWN = ["doc_type_code", "doc_no", "issued_on", "expired_on", "catatan"] as const;

/** Perbarui dokumen kendaraan: berkas baru + tanggal jatuh tempo; dokumen lama otomatis diganti oleh API. */
export function VehicleDocumentDialog({ vehicleId, plate, docTypeCode, onClose }: {
  vehicleId: string;
  plate: string;
  docTypeCode?: string;
  onClose: () => void;
}) {
  const types = useDocumentTypes();
  const add = useAddVehicleDocument(vehicleId);
  const upload = useUploadFile();
  const [formError, setFormError] = useState<string | null>(null);
  const [file, setFile] = useState<File | undefined>();
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<VehicleDocumentValues>({
    resolver: zodResolver(vehicleDocumentSchema),
    defaultValues: { doc_type_code: docTypeCode ?? "", doc_no: "", issued_on: "", expired_on: "", catatan: "" },
  });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    const tooBig = file ? oversize([file]) : null;
    if (tooBig) return setFormError(tooBig);
    try {
      let file_id: string | null = null;
      if (file) {
        const body = new FormData();
        body.set("file", file);
        file_id = (await upload.mutateAsync(body)).file_id;
      }
      await add.mutateAsync({
        doc_type_code: v.doc_type_code,
        doc_no: v.doc_no || null,
        issued_on: v.issued_on || null,
        expired_on: v.expired_on,
        catatan: v.catatan || null,
        file_id,
      });
      toast.success("Dokumen diperbarui.");
      onClose();
    } catch (err) {
      setFormError(applyFieldErrors(err, setError, KNOWN) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  });
  return (
    <DocFormDialog title={`Perbarui dokumen ${plate}`} submitLabel="Simpan dokumen" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Jenis dokumen" error={errors.doc_type_code?.message} {...register("doc_type_code")}>
        <ControlOption value="">Pilih jenis dokumen</ControlOption>
        {types.data?.filter((t) => t.berlaku_untuk === "KENDARAAN").map((t) => (
          <ControlOption key={t.code} value={t.code}>{t.nama}</ControlOption>
        ))}
      </SelectField>
      <TextField label="Nomor dokumen (boleh kosong)" maxLength={100} error={errors.doc_no?.message} {...register("doc_no")} />
      <TextField label="Berlaku mulai (boleh kosong)" type="date" error={errors.issued_on?.message} {...register("issued_on")} />
      <TextField label="Jatuh tempo" type="date" error={errors.expired_on?.message} {...register("expired_on")} />
      <UploadField label="Berkas baru (jpg, png, pdf)" accept=".jpg,.jpeg,.png,.pdf" hint="Dokumen lama otomatis diganti." onChange={(e) => setFile(e.target.files?.[0])} />
      <TextAreaField label="Catatan (boleh kosong)" maxLength={500} error={errors.catatan?.message} {...register("catatan")} />
    </DocFormDialog>
  );
}
