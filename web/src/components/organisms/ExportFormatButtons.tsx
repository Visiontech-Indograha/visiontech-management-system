import { useEffect, useState } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { Download } from "@/components/molecules/Glyphs";
import { TextBlock } from "@/components/molecules/TextBlock";
import { EXPORT_FORMATS, type ExportFormat } from "@/services/exportService";

/**
 * Pilihan format unduhan (PDF, Word, PowerPoint) untuk satu jenis laporan.
 * Semua tombol nonaktif selama ada proses; tombol yang sedang diproses menampilkan "Menyiapkan…".
 */
export function ExportFormatButtons({ label, busy, pendingFormat, disabled, onPick }: {
  label: string;
  busy: boolean;
  pendingFormat?: ExportFormat | null;
  disabled?: boolean;
  onPick: (format: ExportFormat) => void;
}) {
  // Status "Menyiapkan…" langsung saat klik, tanpa menunggu mutasi induk menyala.
  const [clicked, setClicked] = useState<ExportFormat | null>(null);
  const [prevBusy, setPrevBusy] = useState(busy);
  if (prevBusy !== busy) {
    setPrevBusy(busy);
    if (!busy) setClicked(null);
  }
  useEffect(() => {
    if (!clicked) return;
    const t = setTimeout(() => setClicked(null), 3000);
    return () => clearTimeout(t);
  }, [clicked]);
  const isBusy = busy || clicked !== null;
  const shown = clicked ?? pendingFormat;
  return (
    <div role="group" aria-label={`Unduh ${label}`} className="flex flex-wrap items-center gap-2">
      <TextBlock as="span" className="text-sm text-ink">{label}</TextBlock>
      {EXPORT_FORMATS.map((f) => (
        <ActionButton
          key={f.value}
          size="sm"
          variant="outline"
          className="h-11"
          aria-label={`${label} sebagai ${f.label}`}
          disabled={isBusy || disabled}
          onClick={() => {
            setClicked(f.value);
            onPick(f.value);
          }}
        >
          <Download className="mr-1.5 h-3.5 w-3.5" />
          {isBusy && shown === f.value ? "Menyiapkan…" : f.label}
        </ActionButton>
      ))}
    </div>
  );
}
