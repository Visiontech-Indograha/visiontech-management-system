import { useRef, useState } from "react";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ShieldCheck } from "@/components/molecules/Glyphs";
import {
  SignaturePad,
  type SignaturePadHandle,
} from "@/components/molecules/SignaturePad";
import { useSignWorkCompletion } from "@/services/workCompletionService";

interface PmSignatureDialogProps {
  open: boolean;
  completionId: string;
  projectTitle?: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export function PmSignatureDialog({
  open,
  completionId,
  projectTitle,
  onClose,
  onSuccess,
}: PmSignatureDialogProps) {
  const padRef = useRef<SignaturePadHandle | null>(null);
  const [hasSignature, setHasSignature] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const signMutation = useSignWorkCompletion();

  const handleClose = () => {
    setErrorMessage(null);
    setHasSignature(false);
    padRef.current?.clear();
    onClose();
  };

  const handleSubmit = async () => {
    const dataUrl = padRef.current?.getSignatureDataUrl();
    if (!dataUrl) {
      setErrorMessage("Silakan bubuhkan tanda tangan Anda pada area canvas terlebih dahulu.");
      return;
    }

    try {
      await signMutation.mutateAsync({
        id: completionId,
        payload: {
          signature_data_url: dataUrl,
        },
      });
      onSuccess?.();
      handleClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal mengesahkan berita acara penyelesaian.";
      setErrorMessage(msg);
    }
  };

  return (
    <VmsDialog
      open={open}
      title="Pengesahan BAST oleh Project Manager"
      onClose={handleClose}
      className="sm:max-w-lg"
    >
      <div className="space-y-4">
        <div>
          <TextBlock className="text-xs font-semibold uppercase tracking-wider text-mist">
            Proyek
          </TextBlock>
          <TextBlock className="font-semibold text-ink">
            {projectTitle || "Berita Acara Serah Terima"}
          </TextBlock>
          <TextBlock className="mt-1 text-xs text-mist">
            Dengan menandatangani dokumen ini, Anda menyatakan bahwa hasil pekerjaan lapangan dan
            material aktual telah diverifikasi dan disetujui. Dokumen serah terima akan dikunci secara permanen.
          </TextBlock>
        </div>

        {/* Signature Area */}
        <SignaturePad
          ref={padRef}
          label="Tanda Tangan Digital Project Manager"
          onChange={(sig) => {
            setHasSignature(sig);
            if (sig) setErrorMessage(null);
          }}
        />

        {errorMessage && (
          <TextBlock className="text-xs font-medium text-danger">{errorMessage}</TextBlock>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-line">
          <ActionButton type="button" variant="outline" size="sm" onClick={handleClose}>
            <TextBlock as="span">Batal</TextBlock>
          </ActionButton>
          <ActionButton
            type="button"
            variant="default"
            size="sm"
            onClick={handleSubmit}
            disabled={!hasSignature || signMutation.isPending}
          >
            <ShieldCheck className="mr-1.5 h-4 w-4" />
            <TextBlock as="span">
              {signMutation.isPending ? "Mengesahkan..." : "Sahkan dan Kunci Dokumen"}
            </TextBlock>
          </ActionButton>
        </div>
      </div>
    </VmsDialog>
  );
}
