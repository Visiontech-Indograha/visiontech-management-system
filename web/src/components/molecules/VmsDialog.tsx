import { useCallback, useState, type ReactNode } from "react";
import { Dialog as ShadcnDialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../atoms/Dialog";
import { Button } from "../atoms/Button";
import { Text } from "../atoms/Text";
import { cn } from "@/lib/utils";
import { DialogGuardContext, type DialogGuard } from "@/lib/dialogGuard";

/** Dialog untuk konfirmasi dan formulir singkat. */
export function VmsDialog({
  open,
  title,
  onClose,
  children,
  footer,
  className,
  dirty = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  /** Formulir berubah dan belum disimpan: Esc/klik luar/X/Batal meminta konfirmasi di dalam dialog. */
  dirty?: boolean;
}) {
  const [askDiscard, setAskDiscard] = useState(false);
  // Aksi yang tertahan (mis. Batal → onCancel), dijalankan bila pengguna memilih "Tutup tanpa menyimpan".
  const [pending, setPending] = useState<(() => void) | null>(null);

  const guard = useCallback<DialogGuard>(
    (next) => {
      if (!dirty) return next();
      setPending(() => next);
      setAskDiscard(true);
    },
    [dirty],
  );

  return (
    <ShadcnDialog
      open={open}
      onOpenChange={(val) => {
        if (!val) guard(onClose);
      }}
    >
      {/* Formulir panjang (mis. peta lokasi) tetap terjangkau di layar pendek. */}
      <DialogContent className={cn("max-h-[calc(100dvh-2rem)] overflow-y-auto", className)}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        {askDiscard && (
          <div role="alert" className="rounded-control bg-hover p-3 text-sm">
            <Text>Perubahan belum disimpan. Tutup tanpa menyimpan?</Text>
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
          <div className="py-4">{children}</div>
          {footer && <DialogFooter>{footer}</DialogFooter>}
        </DialogGuardContext.Provider>
      </DialogContent>
    </ShadcnDialog>
  );
}
