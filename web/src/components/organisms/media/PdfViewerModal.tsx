/**
 * web/src/components/organisms/media/PdfViewerModal.tsx
 * Modal pratinjau dokumen PDF in-app menggunakan embedded preview stream.
 */

import React from "react";
import { Modal as Dialog, ModalContent as DialogContent, ModalHeader as DialogHeader, ModalTitle as DialogTitle } from "@/components/molecules/Modal";
import { ActionButton as Button } from "@/components/molecules/ActionButton";
import { ExternalLink as LinkTo } from "@/components/molecules/Links";
import { FrameView } from "@/components/molecules/FrameView";
import { toPreviewUrl, toDownloadUrl } from "@/lib/mediaUtils";
import { Download, ExternalLink as ExternalLinkIcon, FileText, Printer } from "@/components/molecules/Glyphs";

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
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-[96vw] sm:max-w-7xl h-[90dvh] flex flex-col p-0 overflow-hidden bg-slate-900 border-slate-700">
        <DialogHeader className="p-4 bg-slate-800 border-b border-slate-700 flex flex-row items-center justify-between space-y-0 text-white">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-red-400" />
            <DialogTitle className="text-base font-semibold text-white truncate max-w-md">
              {title}
            </DialogTitle>
          </div>

          <div className="flex items-center gap-2 pr-6">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrint}
              className="text-xs bg-slate-700 hover:bg-slate-600 text-white border-slate-600 h-8 gap-1.5"
            >
              <Printer className="w-3.5 h-3.5" />
              Cetak
            </Button>
            <LinkTo href={downloadUrl} download>
              <Button
                variant="outline"
                size="sm"
                className="text-xs bg-slate-700 hover:bg-slate-600 text-white border-slate-600 h-8 gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                Unduh
              </Button>
            </LinkTo>
            <LinkTo href={previewUrl} target="_blank" rel="noopener noreferrer">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-slate-300 hover:text-white hover:bg-slate-700 h-8 gap-1.5"
              >
                <ExternalLinkIcon className="w-3.5 h-3.5" />
                Tab Baru
              </Button>
            </LinkTo>
          </div>
        </DialogHeader>

        <div className="flex-1 w-full h-full bg-slate-950 relative">
          <FrameView
            id="pdf-preview-frame"
            src={previewUrl}
            title={title}
            className="w-full h-full border-0"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
};
