/**
 * web/src/components/organisms/media/ImageLightboxModal.tsx
 * Modal Lightbox Gambar Interaktif dengan Zoom, Rotasi, dan Overlay Metadata GPS/Waktu.
 */

import React, { useState } from "react";
import { Modal as Dialog, ModalContent as DialogContent, ModalHeader as DialogHeader, ModalTitle as DialogTitle } from "@/components/molecules/Modal";
import { ActionButton as Button } from "@/components/molecules/ActionButton";
import { ExternalLink as LinkTo } from "@/components/molecules/Links";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { toPreviewUrl, toDownloadUrl } from "@/lib/mediaUtils";
import {
  Clock,
  Download,
  ExternalLink as ExternalLinkIcon,
  ImageIcon,
  MapPin,
  RotateCw,
  User,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from "@/components/molecules/Glyphs";

interface ImageLightboxModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  filePath: string | null | undefined;
  gpsLat?: number | null;
  gpsLng?: number | null;
  timestamp?: string | null;
  uploadedBy?: string | null;
}

export const ImageLightboxModal: React.FC<ImageLightboxModalProps> = ({
  isOpen,
  onClose,
  title = "Pratinjau Foto",
  filePath,
  gpsLat,
  gpsLng,
  timestamp,
  uploadedBy,
}) => {
  const [scale, setScale] = useState<number>(1);
  const [rotation, setRotation] = useState<number>(0);

  if (!filePath) return null;

  const previewUrl = toPreviewUrl(filePath);
  const downloadUrl = toDownloadUrl(filePath);

  const handleZoomIn = () => setScale((prev) => Math.min(prev + 0.25, 3));
  const handleZoomOut = () => setScale((prev) => Math.max(prev - 0.25, 0.5));
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);
  const handleReset = () => {
    setScale(1);
    setRotation(0);
  };

  const hasGps = gpsLat !== null && gpsLat !== undefined && gpsLng !== null && gpsLng !== undefined;

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) {
          handleReset();
          onClose();
        }
      }}
    >
      <DialogContent className="w-[96vw] sm:max-w-7xl h-[90dvh] flex flex-col p-0 overflow-hidden bg-slate-950 border-slate-800 text-white">
        <DialogHeader className="p-4 bg-slate-900 border-b border-slate-800 flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2">
            <ImageIcon className="w-5 h-5 text-sky-400" />
            <DialogTitle className="text-base font-semibold text-white truncate max-w-sm">
              {title}
            </DialogTitle>
          </div>

          <div className="flex items-center gap-1.5 pr-6">
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomIn}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 h-8 px-2"
              title="Perbesar"
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomOut}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 h-8 px-2"
              title="Perkecil"
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRotate}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 h-8 px-2"
              title="Putar 90°"
            >
              <RotateCw className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 h-8 px-2"
              title="Reset Tampilan"
            >
              <RotateCcw className="w-4 h-4" />
            </Button>

            <LinkTo href={downloadUrl} download>
              <Button
                variant="outline"
                size="sm"
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 h-8 px-2 gap-1"
              >
                <Download className="w-4 h-4" />
              </Button>
            </LinkTo>
            <LinkTo href={previewUrl} target="_blank" rel="noopener noreferrer">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-slate-400 hover:text-white hover:bg-slate-800 h-8 px-2"
              >
                <ExternalLinkIcon className="w-4 h-4" />
              </Button>
            </LinkTo>
          </div>
        </DialogHeader>

        {/* Viewport Konten Gambar */}
        <div className="flex-1 w-full h-full relative overflow-auto flex items-center justify-center p-4 bg-slate-950">
          <ImageView
            src={previewUrl}
            alt={title}
            style={{
              transform: `scale(${scale}) rotate(${rotation}deg)`,
              transition: "transform 0.15s ease-out",
            }}
            className="max-h-[65vh] max-w-full object-contain rounded select-none shadow-2xl"
          />

          {/* Overlay Metadata GPS & Timestamp jika ada */}
          {(hasGps || timestamp || uploadedBy) && (
            <div className="absolute bottom-4 left-4 right-4 bg-slate-900/85 backdrop-blur border border-slate-800 rounded-lg p-3 text-xs flex flex-wrap items-center justify-between gap-3 text-slate-300">
              <div className="flex flex-wrap items-center gap-4">
                {hasGps && (
                  <div className="flex items-center gap-1.5 text-sky-400 font-medium">
                    <MapPin className="w-4 h-4 text-sky-400 shrink-0" />
                    <TextBlock as="span">
                      {Number(gpsLat).toFixed(6)}, {Number(gpsLng).toFixed(6)}
                    </TextBlock>
                  </div>
                )}
                {timestamp && (
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-emerald-400 shrink-0" />
                    <TextBlock as="span">{timestamp}</TextBlock>
                  </div>
                )}
                {uploadedBy && (
                  <div className="flex items-center gap-1.5">
                    <User className="w-4 h-4 text-amber-400 shrink-0" />
                    <TextBlock as="span">{uploadedBy}</TextBlock>
                  </div>
                )}
              </div>
              <TextBlock as="span" className="text-[11px] text-slate-500">Zoom: {Math.round(scale * 100)}%</TextBlock>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
