import { useState } from "react";
import { toast } from "sonner";
import { Notice, NoticeDescription, NoticeTitle } from "@/components/molecules/Notice";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import type { TokenBaru } from "@/services/hikvisionService";

/** Menampilkan tautan penerima SEKALI. Dialog ditutup = tautan hilang dari state halaman. */
export function ReceiverLinkDialog({ deviceName, link, onClose }: {
  deviceName: string;
  link: TokenBaru;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link.receiver_url);
      setCopied(true);
      toast.success("Tautan disalin.");
    } catch (err) {
      toast.error(errorMessage(err, "Tautan belum bisa disalin. Pilih tulisan tautan lalu salin sendiri."));
    }
  };
  return (
    <VmsDialog
      open
      title="Tautan penerima"
      onClose={onClose}
      footer={<ActionButton onClick={onClose}>{copied ? "Selesai" : "Tutup"}</ActionButton>}
    >
      <Notice variant="destructive" className="mb-4">
        <NoticeTitle>Simpan sekarang, tidak akan ditampilkan lagi</NoticeTitle>
        <NoticeDescription>
          Pasang tautan ini di mesin {deviceName} agar data absen masuk. Bila hilang, buat tautan baru dan pasang ulang di mesin; tautan lama tidak berlaku lagi.
        </NoticeDescription>
      </Notice>
      <TextBlock aria-label="Tautan penerima" className="mb-3 select-all break-all rounded-panel border border-line bg-muted p-3 text-sm">
        {link.receiver_url}
      </TextBlock>
      <ActionButton variant="outline" onClick={copy}>{copied ? "Sudah disalin" : "Salin tautan"}</ActionButton>
    </VmsDialog>
  );
}
