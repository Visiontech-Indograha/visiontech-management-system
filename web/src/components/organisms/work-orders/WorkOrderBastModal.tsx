import { useRef, useState } from "react";
import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TextField, TextAreaField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { SignaturePad, type SignaturePadHandle } from "@/components/molecules/SignaturePad";
import { FileCheck2 } from "@/components/molecules/Glyphs";
import { useSignBast, type WorkOrder } from "@/services/workOrderService";

interface WorkOrderBastModalProps {
  workOrder: WorkOrder | null;
  onClose: () => void;
}

export function WorkOrderBastModal({
  workOrder,
  onClose,
}: WorkOrderBastModalProps) {
  const [signerName, setSignerName] = useState("");
  const [notes, setNotes] = useState("");
  const sigPadRef = useRef<SignaturePadHandle | null>(null);

  const signMutation = useSignBast(workOrder?.work_order_id || "");

  if (!workOrder) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signerName.trim()) {
      toast.error("Nama penandatangan dari pihak klien wajib diisi");
      return;
    }

    const signatureDataUri = sigPadRef.current?.getSignatureDataUrl();
    if (!signatureDataUri) {
      toast.error("Bubuhkan tanda tangan digital pada kotak yang disediakan");
      return;
    }

    try {
      await signMutation.mutateAsync({
        signer_name: signerName.trim(),
        signature_data_uri: signatureDataUri,
        notes: notes.trim() || undefined,
      });
      toast.success(`Surat serah terima untuk tugas ${workOrder.wo_number} berhasil ditandatangani!`);
      onClose();
    } catch {
      toast.error("Gagal menandatangani surat serah terima");
    }
  };

  return (
    <VmsDialog
      open={Boolean(workOrder)}
      onClose={onClose}
      title={`Tandatangani surat serah terima — ${workOrder.wo_number}`}
      size="xl"
    >
      <FormBlock onSubmit={handleSubmit} noValidate className="space-y-4 pt-2">
        {/* Info Box */}
        <div className="bg-surface-elevated/60 p-3 rounded-lg border border-border text-xs space-y-1">
          <div className="flex items-center justify-between">
            <TextBlock className="font-semibold text-ink text-sm">{workOrder.title}</TextBlock>
            <div className="px-2 py-0.5 bg-emerald-500/10 text-emerald-600 rounded font-semibold text-[11px]">
              <TextBlock as="span">{workOrder.completed_items} / {workOrder.total_items} Item Selesai</TextBlock>
            </div>
          </div>
          <div className="text-muted-foreground">
            <TextBlock as="span">Klien: </TextBlock>
            <TextBlock as="span" className="font-medium text-ink">{workOrder.client_name}</TextBlock>
            <TextBlock as="span"> | Lokasi: </TextBlock>
            <TextBlock as="span" className="font-medium text-ink">{workOrder.site_name || "Pusat"}</TextBlock>
          </div>
        </div>

        <div className="space-y-3">
          <TextField
            label="Nama Lengkap Penandatangan (Klien) *"
            placeholder="Contoh: Budi Santoso (PIC Gedung / Site Manager)"
            value={signerName}
            onChange={(e) => setSignerName(e.target.value)}
            required
          />

          <TextAreaField
            label="Catatan penyelesaian"
            placeholder="Pekerjaan telah diperiksa bersama dan diterima dalam kondisi baik..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
          />

          <div className="space-y-1">
            <SignaturePad
              ref={sigPadRef}
              label="Tanda Tangan Digital Klien *"
              height={160}
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-3 border-t border-border">
          <ActionButton
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={signMutation.isPending}
          >
            <TextBlock as="span">Batal</TextBlock>
          </ActionButton>
          <ActionButton
            type="submit"
            variant="default"
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
            disabled={signMutation.isPending}
          >
            {signMutation.isPending ? (
              <TextBlock as="span">Menyimpan surat serah terima...</TextBlock>
            ) : (
              <div className="flex items-center gap-1.5">
                <FileCheck2 className="h-4 w-4" />
                <TextBlock as="span">Tandatangani dan terbitkan surat serah terima</TextBlock>
              </div>
            )}
          </ActionButton>
        </div>
      </FormBlock>
    </VmsDialog>
  );
}
