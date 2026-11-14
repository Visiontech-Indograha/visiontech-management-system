import { useState } from "react";
import { toast } from "sonner";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { UploadField } from "@/components/molecules/UploadField";
import { errorMessage } from "@/lib/errors";
import { useIdempotencyKey } from "@/lib/idempotency";
import { useBorrowerOptions, useLend, type AssetKind } from "@/services/assetService";
import { wibDate } from "@/services/dailyPlanService";
import { useUploadFile } from "@/services/employeeService";
import { AssetFormDialog } from "./AssetFormDialog";

const fileOf = (form: HTMLFormElement, name: string) =>
  (form.elements.namedItem(name) as HTMLInputElement | null)?.files?.[0];

/**
 * Serah aset ke pihak luar perusahaan (klien sewa, subkontraktor): pilih penerima, tanggal harus kembali (opsional),
 * dokumen serah terima (opsional), foto (opsional). Tanpa jadwal harian. Aturan STNK/KIR dijaga API.
 */
export function AssetLendExternalDialog({ kind, assetId, assetName, officeId, onClose }: {
  kind: AssetKind;
  assetId: string;
  assetName: string;
  officeId: string;
  onClose: () => void;
}) {
  const lend = useLend();
  const upload = useUploadFile();
  const [q, setQ] = useState("");
  const [borrowerId, setBorrowerId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const borrowers = useBorrowerOptions(q, true, officeId);
  const idem = useIdempotencyKey(JSON.stringify({ kind, assetId, borrowerId, dueDate }));
  const today = wibDate();

  const send = async (file?: File) => {
    if (!file) return null;
    const body = new FormData();
    body.set("file", file);
    return (await upload.mutateAsync(body)).file_id;
  };

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    if (!borrowerId) return setFormError("Pilih penerima.");
    if (dueDate && dueDate < today) return setFormError("Tanggal harus kembali tidak boleh sebelum hari ini.");
    const form = e.currentTarget;
    try {
      const bast_file_id = await send(fileOf(form, "handover_doc"));
      const handover_file_id = await send(fileOf(form, "handover_photo"));
      await lend.mutateAsync({
        body: {
          asset_type: kind,
          ...(kind === "TOOL" ? { tool_id: assetId } : { vehicle_id: assetId }),
          external_borrower_id: borrowerId,
          due_date: dueDate || null,
          bast_file_id,
          handover_file_id,
        },
        idempotencyKey: idem.key,
      });
      idem.renew();
      toast.success(`${assetName} diserahkan.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };

  return (
    <AssetFormDialog title={`Serahkan ${assetName} ke pihak luar`} submitLabel="Serahkan"
      submitting={lend.isPending || upload.isPending} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextBlock className="mb-3 text-sm text-mist">Penerima belum ada? Tambahkan lewat tombol Penerima luar di atas daftar.</TextBlock>
      <TextField label="Cari penerima" value={q} onChange={(e) => setQ(e.target.value)} hint="Awal nama penerima" />
      <SelectField label="Penerima" value={borrowerId} onChange={(e) => setBorrowerId(e.target.value)}>
        <ControlOption value="">Pilih penerima</ControlOption>
        {borrowers.data?.map((b) => (
          <ControlOption key={b.borrower_id} value={b.borrower_id}>{b.instansi ? `${b.nama} · ${b.instansi}` : b.nama}</ControlOption>
        ))}
      </SelectField>
      <TextField label="Tanggal harus kembali (opsional)" type="date" min={today} value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
      <UploadField name="handover_doc" label="Dokumen serah terima (opsional)" accept=".pdf,.jpg,.jpeg,.png" hint="Surat atau foto tanda terima yang sudah ditandatangani." />
      <UploadField name="handover_photo" label="Foto serah terima (opsional)" accept=".jpg,.jpeg,.png" />
    </AssetFormDialog>
  );
}
