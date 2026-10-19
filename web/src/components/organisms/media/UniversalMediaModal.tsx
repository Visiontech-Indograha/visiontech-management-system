/**
 * web/src/components/organisms/media/UniversalMediaModal.tsx
 * Modal universal dispatcher untuk seluruh jenis dokumen dan media di VMS.
 * Secara cerdas membedakan pratinjau gambar (lightbox interaktif), PDF (in-app embed reader),
 * dan dokumen perkantoran (Word, Excel, PowerPoint) dengan tombol aksi unduh langsung.
 */

import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/atoms/Dialog";
import { Button } from "@/components/atoms/Button";
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
  ExternalLink,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Presentation,
} from "lucide-react";

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
        return <FileCheck className="w-16 h-16 text-slate-400" />;
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
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md p-6 bg-slate-900 border-slate-800 text-white shadow-2xl rounded-xl">
        <DialogHeader className="space-y-1">
          <DialogTitle className="text-base font-semibold text-white">
            {title || "Unduh Dokumen"}
          </DialogTitle>
          <p className="text-xs text-slate-400">{getCategoryLabel()}</p>
        </DialogHeader>

        <div className="py-6 flex flex-col items-center justify-center text-center space-y-3">
          <div className="p-4 bg-slate-800/80 rounded-2xl border border-slate-700/60 shadow-inner">
            {getDocIcon()}
          </div>
          <div className="max-w-xs">
            <p className="text-sm font-medium text-slate-200 truncate" title={fileName}>
              {fileName}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Dokumen perkantoran memerlukan aplikasi lokal (Office/WPS/LibreOffice) untuk membuka format berkas ini secara utuh.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-2 border-t border-slate-800">
          <a href={downloadUrl} download className="w-full">
            <Button
              className="w-full bg-sky-600 hover:bg-sky-500 text-white font-medium h-10 gap-2 text-sm shadow-md"
            >
              <Download className="w-4 h-4" />
              Unduh Berkas Sekarang
            </Button>
          </a>

          <div className="flex items-center gap-2">
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1"
            >
              <Button
                variant="outline"
                className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 h-9 gap-1.5 text-xs"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Buka di Tab Baru
              </Button>
            </a>
            <Button
              variant="ghost"
              onClick={onClose}
              className="flex-1 text-slate-400 hover:text-white hover:bg-slate-800 h-9 text-xs"
            >
              Tutup
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
