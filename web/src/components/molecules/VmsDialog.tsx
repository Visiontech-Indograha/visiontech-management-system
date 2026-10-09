import { type ReactNode } from "react";
import { Dialog as ShadcnDialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../atoms/Dialog";

/** Dialog untuk konfirmasi dan formulir singkat. */
export function VmsDialog({
  open,
  title,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <ShadcnDialog open={open} onOpenChange={(val) => !val && onClose()}>
      {/* Formulir panjang (mis. peta lokasi) tetap terjangkau di layar pendek. */}
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="py-4">{children}</div>
        {footer && <DialogFooter>{footer}</DialogFooter>}
      </DialogContent>
    </ShadcnDialog>
  );
}
