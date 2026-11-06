import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";

/** Petunjuk saat akun sudah aktif di batas perangkat (4 perangkat): cara mengeluarkan perangkat lama. */
export function DeviceLimitHelpDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <VmsDialog
      open={open}
      title="Cara mengeluarkan perangkat lama"
      onClose={onClose}
      footer={<ActionButton onClick={onClose}>Mengerti</ActionButton>}
    >
      <TextBlock className="mb-3 text-sm">
        Satu akun bisa aktif di maksimal 4 perangkat. Untuk masuk di perangkat baru, keluarkan salah satu perangkat lama:
      </TextBlock>
      <ListBlock as="ol" className="list-decimal space-y-2 pl-5 text-sm">
        <ListEntry>Buka aplikasi atau web Visiontech di perangkat lama yang masih aktif, lalu masuk seperti biasa.</ListEntry>
        <ListEntry>Buka menu Akun dan keamanan, lalu bagian Perangkat yang masuk.</ListEntry>
        <ListEntry>Pilih Keluarkan pada perangkat yang sudah tidak dipakai.</ListEntry>
        <ListEntry>Kembali ke halaman ini dan masuk lagi di perangkat baru.</ListEntry>
      </ListBlock>
      <TextBlock className="mt-3 text-sm text-mist">
        Tidak punya akses ke perangkat lama? Minta HR atau admin mengosongkan slot perangkat akun Anda.
      </TextBlock>
    </VmsDialog>
  );
}
