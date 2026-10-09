import { useRef } from "react";
import { errorMessage } from "@/lib/errors";
import { useHtmlDocument } from "@/services/workPlanService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { Modal, ModalContent, ModalFooter, ModalHeader, ModalTitle } from "@/components/molecules/Modal";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FrameView } from "@/components/molecules/FrameView";

/**
 * Tampilan dokumen SK siap cetak A4 ("Sunting SK", flowchart SK2-C). Isi HTML dari server — templat yang sama
 * dengan PDF terbit, termasuk tanda tangan & QR bila dokumen sudah terbit. Dirender di iframe ber-sandbox.
 */
export function PlanPreviewDialog({
  title,
  path,
  editTo,
  onClose,
}: {
  title: string;
  path: string;
  editTo?: string;
  onClose: () => void;
}) {
  const doc = useHtmlDocument(path);
  const frame = useRef<HTMLIFrameElement>(null);
  return (
    <Modal open onOpenChange={(v) => !v && onClose()}>
      <ModalContent className="flex max-h-[calc(100dvh-1rem)] w-[calc(100vw-1rem)] max-w-4xl flex-col">
        <ModalHeader>
          <ModalTitle>{title}</ModalTitle>
        </ModalHeader>
        <div className="min-h-0 flex-1 overflow-auto rounded-control bg-canvas p-2">
          {doc.isPending && <LoadingBar className="h-[60vh] w-full" />}
          {doc.isError && <TextBlock className="p-4 text-sm text-danger">{errorMessage(doc.error)}</TextBlock>}
          {doc.data && (
            <FrameView
              ref={frame}
              title={title}
              srcDoc={doc.data}
              sandbox="allow-same-origin allow-modals"
              className="mx-auto block h-[70vh] w-full max-w-[210mm] bg-white shadow-card"
            />
          )}
        </div>
        <ModalFooter className="gap-2">
          <ActionButton variant="outline" onClick={onClose}>
            Tutup
          </ActionButton>
          <ActionButton variant="outline" disabled={!doc.data} onClick={() => frame.current?.contentWindow?.print()}>
            Cetak
          </ActionButton>
          {editTo && (
            <ActionButton asChild>
              <InlineLink to={editTo}>Ubah isi</InlineLink>
            </ActionButton>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
