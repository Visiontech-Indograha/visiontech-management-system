import { useRef } from "react";
import { errorMessage } from "@/lib/errors";
import { useHtmlDocument } from "@/services/workPlanService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { Modal, ModalContent, ModalFooter, ModalHeader, ModalTitle } from "@/components/molecules/Modal";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { ExternalLink, InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FrameView } from "@/components/molecules/FrameView";

/**
 * Tampilan dokumen rencana kerja siap cetak A4 ("Sunting rencana kerja", flowchart SK2-C). Isi HTML dari server — templat yang sama
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
        <ModalFooter className="flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <TextBlock as="span" className="text-xs font-semibold text-mist mr-1">Unduh Dokumen:</TextBlock>
            <ExternalLink
              href={path.replace("/preview", "/export?format=pdf")}
              target="_blank"
              rel="noreferrer"
              download
              className="inline-flex items-center gap-1 rounded-control border border-line bg-surface px-2.5 py-1 text-xs font-medium text-lens hover:bg-hover hover:border-primary transition-colors"
            >
              <TextBlock as="span">📕</TextBlock> <TextBlock as="span">PDF</TextBlock>
            </ExternalLink>
            <ExternalLink
              href={path.replace("/preview", "/export?format=docx")}
              target="_blank"
              rel="noreferrer"
              download
              className="inline-flex items-center gap-1 rounded-control border border-line bg-surface px-2.5 py-1 text-xs font-medium text-lens hover:bg-hover hover:border-primary transition-colors"
            >
              <TextBlock as="span">📘</TextBlock> <TextBlock as="span">Word (.docx)</TextBlock>
            </ExternalLink>
            <ExternalLink
              href={path.replace("/preview", "/export?format=xlsx")}
              target="_blank"
              rel="noreferrer"
              download
              className="inline-flex items-center gap-1 rounded-control border border-line bg-surface px-2.5 py-1 text-xs font-medium text-lens hover:bg-hover hover:border-primary transition-colors"
            >
              <TextBlock as="span">📗</TextBlock> <TextBlock as="span">Excel (.xlsx)</TextBlock>
            </ExternalLink>
            <ExternalLink
              href={path.replace("/preview", "/export?format=pptx")}
              target="_blank"
              rel="noreferrer"
              download
              className="inline-flex items-center gap-1 rounded-control border border-line bg-surface px-2.5 py-1 text-xs font-medium text-lens hover:bg-hover hover:border-primary transition-colors"
            >
              <TextBlock as="span">📙</TextBlock> <TextBlock as="span">PPTX</TextBlock>
            </ExternalLink>
          </div>

          <div className="flex items-center gap-2">
            <ActionButton variant="outline" disabled={!doc.data} onClick={() => frame.current?.contentWindow?.print()}>
              Cetak
            </ActionButton>
            {editTo && (
              <ActionButton asChild>
                <InlineLink to={editTo}>Ubah isi</InlineLink>
              </ActionButton>
            )}
            <ActionButton variant="default" onClick={onClose}>
              Tutup
            </ActionButton>
          </div>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
