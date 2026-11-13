import { ActionButton } from "@/components/molecules/ActionButton";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { TextBlock } from "@/components/molecules/TextBlock";

interface Props {
  earlyLeave: { effH: number; effM: number } | null;
  onCancelEarlyLeave: () => void;
  onConfirmEarlyLeave: () => void;
  encouragement: string | null;
  onCloseEncouragement: () => void;
}

/** Dialog konfirmasi pulang cepat dan ucapan terima kasih setelah absen pulang (kartu absen kantor web). */
export function OfficeCheckOutDialogs({
  earlyLeave,
  onCancelEarlyLeave,
  onConfirmEarlyLeave,
  encouragement,
  onCloseEncouragement,
}: Props) {
  return (
    <>
      {earlyLeave && (
        <VmsDialog
          open={!!earlyLeave}
          title="Waktu Kerja Belum Mencapai 8 Jam"
          onClose={onCancelEarlyLeave}
          footer={
            <div className="flex w-full justify-end gap-2">
              <ActionButton variant="outline" className="h-11" onClick={onCancelEarlyLeave}>
                Batal
              </ActionButton>
              <ActionButton className="h-11" onClick={onConfirmEarlyLeave}>
                Lanjutkan Pulang Cepat
              </ActionButton>
            </div>
          }
        >
          <TextBlock className="text-sm leading-relaxed text-ink">
            {`Waktu kerja kamu saat ini baru ${earlyLeave.effH} jam ${earlyLeave.effM} menit (belum mencapai 8 jam kerja efektif, karena 1 jam istirahat tidak termasuk jam kerja).`}
          </TextBlock>
          <TextBlock className="mt-2 text-sm text-mist">
            Jika tetap melanjutkan pulang sekarang, absensi hari ini akan dicatat dengan keterangan Pulang Cepat. Yakin ingin tetap absen pulang?
          </TextBlock>
        </VmsDialog>
      )}
      {encouragement && (
        <VmsDialog
          open={!!encouragement}
          title="Terima Kasih Atas Kerja Kerasmu! 🌟"
          onClose={onCloseEncouragement}
          footer={
            <ActionButton className="h-11 w-full" onClick={onCloseEncouragement}>
              Tutup & Selamat Beristirahat
            </ActionButton>
          }
        >
          <div className="space-y-3 py-2 text-center">
            <TextBlock className="text-4xl">🌟💪</TextBlock>
            <TextBlock className="text-base font-medium leading-relaxed text-ink">{encouragement}</TextBlock>
          </div>
        </VmsDialog>
      )}
    </>
  );
}
