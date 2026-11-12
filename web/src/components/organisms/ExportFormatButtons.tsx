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
          disabled={busy || disabled}
          onClick={() => onPick(f.value)}
        >
          <Download className="mr-1.5 h-3.5 w-3.5" />
          {busy && pendingFormat === f.value ? "Menyiapkan…" : f.label}
        </ActionButton>
      ))}
    </div>
  );
}
