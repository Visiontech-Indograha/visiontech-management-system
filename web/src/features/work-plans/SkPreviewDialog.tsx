import { useRef } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/atoms/Button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/atoms/Dialog";
import { Skeleton } from "@/components/atoms/Skeleton";
import { errorMessage } from "@/lib/errors";
import { useHtmlDocument } from "./api";

/**
 * Tampilan dokumen SK siap cetak A4 ("Sunting SK", flowchart SK2-C). Isi HTML dari server — templat yang sama
 * dengan PDF terbit, termasuk tanda tangan & QR bila dokumen sudah terbit. Dirender di iframe ber-sandbox.
 */
export function SkPreviewDialog({
  title,
  path,
  editTo,
  onClose,
}: {
  title: string;
  path: string;
  editTo?: string;
  onClose: () => void;
}) {
  const doc = useHtmlDocument(path);
  const frame = useRef<HTMLIFrameElement>(null);
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="flex max-h-[calc(100dvh-1rem)] w-[calc(100vw-1rem)] max-w-4xl flex-col">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-auto rounded-control bg-canvas p-2">
          {doc.isPending && <Skeleton className="h-[60vh] w-full" />}
          {doc.isError && <p className="p-4 text-sm text-danger">{errorMessage(doc.error)}</p>}
          {doc.data && (
            <iframe
              ref={frame}
              title={title}
              srcDoc={doc.data}
              sandbox="allow-same-origin allow-modals"
              className="mx-auto block h-[70vh] w-full max-w-[210mm] bg-white shadow-card"
            />
          )}
        </div>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose}>
            Tutup
          </Button>
          <Button variant="outline" disabled={!doc.data} onClick={() => frame.current?.contentWindow?.print()}>
            Cetak
          </Button>
          {editTo && (
            <Button asChild>
              <Link to={editTo}>Ubah isi</Link>
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
