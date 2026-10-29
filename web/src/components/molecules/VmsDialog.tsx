import { useState, type ReactNode } from "react";
import { Dialog as ShadcnDialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../atoms/Dialog";
import { Button } from "../atoms/Button";
import { Text } from "../atoms/Text";
import { cn } from "@/lib/utils";

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
  /** Formulir berubah dan belum disimpan: menutup lewat Esc/klik luar/X meminta konfirmasi di dalam dialog. */
  dirty?: boolean;
}) {
  const [askDiscard, setAskDiscard] = useState(false);

  return (
    <ShadcnDialog
      open={open}
      onOpenChange={(val) => {
        if (val) return;
        if (dirty) {
          setAskDiscard(true);
          return;
        }
        onClose();
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
              <Button variant="outline" size="sm" onClick={() => setAskDiscard(false)}>
                Lanjut mengedit
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  setAskDiscard(false);
                  onClose();
                }}
              >
                Tutup tanpa menyimpan
              </Button>
            </div>
          </div>
        )}
        <div className="py-4">{children}</div>
        {footer && <DialogFooter>{footer}</DialogFooter>}
      </DialogContent>
    </ShadcnDialog>
  );
}
