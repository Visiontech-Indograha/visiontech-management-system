/**
 * web/src/components/organisms/media/PdfViewerModal.tsx
 * Modal pratinjau dokumen PDF in-app menggunakan embedded preview stream.
 */

import React from "react";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton as Button } from "@/components/molecules/ActionButton";
import { ExternalLink as LinkTo } from "@/components/molecules/Links";
import { FrameView } from "@/components/molecules/FrameView";
import { toPreviewUrl, toDownloadUrl } from "@/lib/mediaUtils";
import { Download, ExternalLink as ExternalLinkIcon, Printer } from "@/components/molecules/Glyphs";

interface PdfViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  filePath: string | null | undefined;
}

export const PdfViewerModal: React.FC<PdfViewerModalProps> = ({
  isOpen,
  onClose,
  title = "Pratinjau Dokumen PDF",
  filePath,
}) => {
  if (!filePath) return null;

  const previewUrl = toPreviewUrl(filePath);
  const downloadUrl = toDownloadUrl(filePath);

  const handlePrint = () => {
    const iframe = document.getElementById("pdf-preview-frame") as HTMLIFrameElement;
    if (iframe?.contentWindow) {
      iframe.contentWindow.focus();
      iframe.contentWindow.print();
    } else {
      window.open(previewUrl, "_blank");
    }
  };

  return (
    <VmsDialog open={isOpen} onClose={onClose} title={title} fullscreen>
      <div className="flex items-center justify-end gap-2 border-b border-line px-4 py-2">
        <Button variant="outline" size="sm" onClick={handlePrint} className="h-11 gap-1.5 text-xs">
          <Printer className="h-3.5 w-3.5" />
          Cetak
        </Button>
        <LinkTo href={downloadUrl} download>
          <Button variant="outline" size="sm" className="h-11 gap-1.5 text-xs">
            <Download className="h-3.5 w-3.5" />
            Unduh
          </Button>
        </LinkTo>
        <LinkTo href={previewUrl} target="_blank" rel="noopener noreferrer">
          <Button variant="ghost" size="sm" className="h-11 gap-1.5 text-xs">
            <ExternalLinkIcon className="h-3.5 w-3.5" />
            Tab Baru
          </Button>
        </LinkTo>
      </div>
      <div className="relative h-full w-full flex-1">
        <FrameView id="pdf-preview-frame" src={previewUrl} title={title} className="h-full w-full border-0" />
      </div>
    </VmsDialog>
  );
};
