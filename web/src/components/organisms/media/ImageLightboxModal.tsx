/**
 * web/src/components/organisms/media/ImageLightboxModal.tsx
 * Modal Lightbox Gambar Interaktif dengan Zoom, Rotasi, dan Overlay Metadata GPS/Waktu.
 */

import React, { useState } from "react";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton as Button } from "@/components/molecules/ActionButton";
import { ExternalLink as LinkTo } from "@/components/molecules/Links";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { toPreviewUrl, toDownloadUrl } from "@/lib/mediaUtils";
import {
  Clock,
  Download,
  ExternalLink as ExternalLinkIcon,
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
    <VmsDialog
      open={isOpen}
      title={title}
      fullscreen
      onClose={() => {
        handleReset();
        onClose();
      }}
    >
      <div className="flex items-center justify-end gap-1.5 border-b border-line px-4 py-2">
        <Button variant="outline" size="sm" onClick={handleZoomIn} className="h-11 px-2 text-xs" title="Perbesar" aria-label="Perbesar">
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="sm" onClick={handleZoomOut} className="h-11 px-2 text-xs" title="Perkecil" aria-label="Perkecil">
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="sm" onClick={handleRotate} className="h-11 px-2 text-xs" title="Putar 90°" aria-label="Putar 90 derajat">
          <RotateCw className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="sm" onClick={handleReset} className="h-11 px-2 text-xs" title="Reset Tampilan" aria-label="Atur ulang tampilan">
          <RotateCcw className="h-4 w-4" />
        </Button>
        <LinkTo href={downloadUrl} download>
          <Button variant="outline" size="sm" className="h-11 gap-1 px-2 text-xs" aria-label="Unduh">
            <Download className="h-4 w-4" />
          </Button>
        </LinkTo>
        <LinkTo href={previewUrl} target="_blank" rel="noopener noreferrer">
          <Button variant="ghost" size="sm" className="h-11 px-2 text-xs" aria-label="Buka di tab baru">
            <ExternalLinkIcon className="h-4 w-4" />
          </Button>
        </LinkTo>
      </div>

        {/* Viewport Konten Gambar */}
        <div className="flex-1 w-full h-full relative overflow-auto flex items-center justify-center p-4 bg-muted">
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
            <div className="absolute bottom-4 left-4 right-4 bg-background border border-line rounded-lg p-3 text-xs flex flex-wrap items-center justify-between gap-3 text-foreground">
              <div className="flex flex-wrap items-center gap-4">
                {hasGps && (
                  <div className="flex items-center gap-1.5 text-primary font-medium">
                    <MapPin className="w-4 h-4 text-primary shrink-0" />
                    <TextBlock as="span">
                      {Number(gpsLat).toFixed(6)}, {Number(gpsLng).toFixed(6)}
                    </TextBlock>
                  </div>
                )}
                {timestamp && (
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-primary shrink-0" />
                    <TextBlock as="span">{timestamp}</TextBlock>
                  </div>
                )}
                {uploadedBy && (
                  <div className="flex items-center gap-1.5">
                    <User className="w-4 h-4 text-primary shrink-0" />
                    <TextBlock as="span">{uploadedBy}</TextBlock>
                  </div>
                )}
              </div>
              <TextBlock as="span" className="text-xs text-muted-foreground">Zoom: {Math.round(scale * 100)}%</TextBlock>
            </div>
          )}
        </div>
    </VmsDialog>
  );
};
