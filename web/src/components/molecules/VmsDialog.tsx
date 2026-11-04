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

/** Dialog VMS: responsif dan proporsional. Di ponsel tampil sebagai bottom-sheet lega, di desktop lega & adaptif. */
export function VmsDialog({
  open,
  title,
  onClose,
  children,
  footer,
  className,
  size = "auto",
  dirty = false,
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
      <DialogContent className={cn(sizeClass, "p-5 sm:p-6", className)}>
        {/* Indikator pegangan seret ergonomis di ponsel */}
        <div className="mx-auto -mt-2 mb-2 h-1.5 w-12 rounded-full bg-border sm:hidden" aria-hidden />
        
        <DialogHeader className="shrink-0">
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        {askDiscard && (
          <div role="alert" className="shrink-0 rounded-control border border-warning-border bg-warning-bg p-3 text-sm my-1">
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

        <DialogGuardContext.Provider value={guard}>
          {/* Konten scrollable mandiri yang fleksibel dan tidak terpotong */}
          <div className="flex-1 min-h-0 overflow-y-auto pr-1 py-1">
            {children}
          </div>
          {footer && <DialogFooter>{footer}</DialogFooter>}
        </DialogGuardContext.Provider>
      </DialogContent>
    </ShadcnDialog>
  );
}
