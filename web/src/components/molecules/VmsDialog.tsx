import { useCallback, useState, type ReactNode } from "react";
import { Dialog as ShadcnDialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../atoms/Dialog";
import { Button } from "../atoms/Button";
import { Text } from "../atoms/Text";
import { cn } from "@/lib/utils";
import { DialogGuardContext, type DialogGuard } from "@/lib/dialogGuard";

export type VmsDialogSize = "auto" | "sm" | "md" | "lg" | "xl" | "2xl" | "full";

const SIZE_CLASSES: Record<VmsDialogSize, string> = {
  // Lebar mengikuti isi (tabel/peta/form), minimal lega, maksimal 96% layar.
  auto: "sm:w-fit sm:min-w-[min(36rem,96vw)] sm:max-w-[min(80rem,96vw)]",
  sm: "sm:max-w-md",
  md: "sm:max-w-xl",
  lg: "sm:max-w-5xl",
  xl: "sm:max-w-6xl",
  "2xl": "sm:max-w-7xl sm:w-[94vw]",
  full: "sm:w-[96vw] sm:max-w-[1500px] sm:h-[92vh]",
};

/**
 * Dialog VMS: responsif dan proporsional. Di ponsel tampil sebagai bottom-sheet lega, di desktop lega & adaptif.
 * Tata letak: header dan footer selalu terlihat; hanya badan (`children`) yang menggulir. Tinggi total
 * dibatasi 90% layar (dvh di ponsel) sehingga footer tidak pernah terpotong di tepi bawah viewport.
 */
export function VmsDialog({
  open,
  title,
  onClose,
  children,
  footer,
  className,
  size = "auto",
  dirty = false,
  hideClose = false,
  onOpenAutoFocus,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  size?: VmsDialogSize;
  /** Formulir berubah dan belum disimpan: Esc/klik luar/X/Batal meminta konfirmasi di dalam dialog. */
  dirty?: boolean;
  /** Sembunyikan tombol tutup (X), mis. panduan wajib baca yang harus dibaca penuh dulu. */
  hideClose?: boolean;
  /** Fokus awal saat dialog dibuka; panggil `e.preventDefault()` untuk mengatur fokus sendiri. */
  onOpenAutoFocus?: (event: Event) => void;
}) {
  const [askDiscard, setAskDiscard] = useState(false);
  const [pending, setPending] = useState<(() => void) | null>(null);

  const guard = useCallback<DialogGuard>(
    (next) => {
      if (!dirty) return next();
      setPending(() => next);
      setAskDiscard(true);
    },
    [dirty],
  );

  const sizeClass = SIZE_CLASSES[size] ?? SIZE_CLASSES.auto;

  return (
    <ShadcnDialog
      open={open}
      onOpenChange={(val) => {
        if (!val) guard(onClose);
      }}
    >
      <DialogContent
        showCloseButton={!hideClose}
        onOpenAutoFocus={onOpenAutoFocus}
        className={cn(
          sizeClass,
          // Kerangka kolom: header & footer tetap, badan menggulir. Padding diatur per bagian di bawah.
          "flex max-h-[90dvh] flex-col gap-0 overflow-hidden p-0 sm:max-h-[90vh] sm:p-0",
          className,
        )}
      >
        {/* Indikator pegangan seret ergonomis di ponsel */}
        <div className="mx-auto mt-2 h-1.5 w-12 shrink-0 rounded-full bg-border sm:hidden" aria-hidden />

        <div className="shrink-0 px-5 pt-4 pr-14 sm:px-6 sm:pt-6">
          <DialogHeader className="pb-0 pr-0">
            <DialogTitle>{title}</DialogTitle>
          </DialogHeader>
        </div>

        <DialogGuardContext.Provider value={guard}>
          {askDiscard && (
            <div role="alert" className="mx-5 mt-3 shrink-0 rounded-control border border-warning-border bg-warning-bg p-3 text-sm sm:mx-6">
              <Text className="font-medium text-warning">Perubahan belum disimpan. Tutup tanpa menyimpan?</Text>
              <div className="mt-2 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setAskDiscard(false);
                    setPending(null);
                  }}
                >
                  Lanjut mengedit
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    const next = pending ?? onClose;
                    setAskDiscard(false);
                    setPending(null);
                    next();
                  }}
                >
                  Tutup tanpa menyimpan
                </Button>
              </div>
            </div>
          )}

          {/* Badan dialog: satu-satunya bagian yang menggulir */}
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-3 pr-4 sm:px-6 sm:pr-5">
            {children}
          </div>

          {footer && (
            <DialogFooter className="mx-0 mt-0 mb-0 shrink-0 border-t border-line bg-background px-5 py-3.5 backdrop-blur-none sm:mx-0 sm:mb-0 sm:px-6">
              {footer}
            </DialogFooter>
          )}
        </DialogGuardContext.Provider>
      </DialogContent>
    </ShadcnDialog>
  );
}
