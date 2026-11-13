/**
 * web/src/components/organisms/media/UniversalMediaModal.tsx
 * Modal universal dispatcher untuk seluruh jenis dokumen dan media di VMS.
 * Secara cerdas membedakan pratinjau gambar (lightbox interaktif), PDF (in-app embed reader),
 * dan dokumen perkantoran (Word, Excel, PowerPoint) dengan tombol aksi unduh langsung.
 */

import React from "react";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton as Button } from "@/components/molecules/ActionButton";
import { ExternalLink as LinkTo } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import {
  detectFileCategory,
  toDownloadUrl,
  toPreviewUrl,
  type FileCategory,
} from "@/lib/mediaUtils";
import { ImageLightboxModal } from "./ImageLightboxModal";
import { PdfViewerModal } from "./PdfViewerModal";
import {
  Download,
  ExternalLink as ExternalLinkIcon,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Presentation,
} from "@/components/molecules/Glyphs";

export interface UniversalMediaModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  filePath: string | null | undefined;
  gpsLat?: number | null;
  gpsLng?: number | null;
  timestamp?: string | null;
  uploadedBy?: string | null;
}

export const UniversalMediaModal: React.FC<UniversalMediaModalProps> = ({
  isOpen,
  onClose,
  title,
  filePath,
  gpsLat,
  gpsLng,
  timestamp,
  uploadedBy,
}) => {
  if (!isOpen || !filePath) return null;

  const category: FileCategory = detectFileCategory(filePath);

  if (category === "image") {
    return (
      <ImageLightboxModal
        isOpen={isOpen}
        onClose={onClose}
        title={title || "Pratinjau Foto"}
        filePath={filePath}
        gpsLat={gpsLat}
        gpsLng={gpsLng}
        timestamp={timestamp}
        uploadedBy={uploadedBy}
      />
    );
  }

  if (category === "pdf") {
    return (
      <PdfViewerModal
        isOpen={isOpen}
        onClose={onClose}
        title={title || "Pratinjau Dokumen PDF"}
        filePath={filePath}
      />
    );
  }

  // Dokumen Office (Word, Excel, PPT) atau jenis lainnya
  const downloadUrl = toDownloadUrl(filePath);
  const previewUrl = toPreviewUrl(filePath);
  const fileName = filePath.split("/").pop() || filePath;

  const getDocIcon = () => {
    switch (category) {
      case "word":
        return <FileText className="w-16 h-16 text-blue-500" />;
      case "excel":
        return <FileSpreadsheet className="w-16 h-16 text-emerald-500" />;
      case "powerpoint":
        return <Presentation className="w-16 h-16 text-orange-500" />;
      default:
        return <FileCheck className="w-16 h-16 text-muted-foreground" />;
    }
  };

  const getCategoryLabel = () => {
    switch (category) {
      case "word":
        return "Dokumen Microsoft Word (.docx)";
      case "excel":
        return "Lembar Kerja Microsoft Excel (.xlsx)";
      case "powerpoint":
        return "Presentasi Microsoft PowerPoint (.pptx)";
      default:
        return "Berkas Lampiran";
    }
  };

  return (
    <VmsDialog open={isOpen} onClose={onClose} title={title || "Unduh Dokumen"} size="md">
      <TextBlock as="p" className="text-xs text-muted-foreground">{getCategoryLabel()}</TextBlock>

      <div className="flex flex-col items-center justify-center space-y-3 py-6 text-center">
        <div className="rounded-2xl border border-line bg-muted p-4">{getDocIcon()}</div>
        <div className="max-w-xs">
          <TextBlock as="p" className="truncate text-sm font-medium text-foreground" title={fileName}>
            {fileName}
          </TextBlock>
          <TextBlock as="p" className="mt-1 text-xs text-muted-foreground">
            Dokumen perkantoran memerlukan aplikasi lokal (Office/WPS/LibreOffice) untuk membuka format berkas ini secara utuh.
          </TextBlock>
        </div>
      </div>

      <div className="flex flex-col gap-2 border-t border-line pt-2">
        <LinkTo href={downloadUrl} download className="w-full">
          <Button className="h-11 w-full gap-2 text-sm font-medium">
            <Download className="h-4 w-4" />
            Unduh Berkas Sekarang
          </Button>
        </LinkTo>
        <div className="flex items-center gap-2">
          <LinkTo href={previewUrl} target="_blank" rel="noopener noreferrer" className="flex-1">
            <Button variant="outline" className="h-11 w-full gap-1.5 text-xs">
              <ExternalLinkIcon className="h-3.5 w-3.5" />
              Buka di Tab Baru
            </Button>
          </LinkTo>
          <Button variant="ghost" onClick={onClose} className="h-11 flex-1 text-xs">
            Tutup
          </Button>
        </div>
      </div>
    </VmsDialog>
  );
};
