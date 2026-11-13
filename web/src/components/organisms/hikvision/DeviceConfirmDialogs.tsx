import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { errorMessage } from "@/lib/errors";
import { useDeleteDevice, useRenewReceiver, useUpdateDevice, type Perangkat, type TokenBaru } from "@/services/hikvisionService";

/** Ganti mode Bayangan <-> Aktif; menjelaskan akibatnya sebelum jalan. */
export function DeviceModeDialog({ device, onClose }: { device: Perangkat; onClose: () => void }) {
  const update = useUpdateDevice(device.device_id);
  const [error, setError] = useState<string | null>(null);
  const toActive = device.mode === "SHADOW";
  const confirm = async () => {
    setError(null);
    try {
      await update.mutateAsync({ mode: toActive ? "AKTIF" : "SHADOW" });
      toast.success(toActive ? "Mesin sekarang dipakai untuk absensi." : "Mesin kembali ke mode Bayangan.");
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Mode belum bisa diganti. Coba lagi."));
    }
  };
  return (
    <ConfirmDialog
      open
      title={toActive ? "Jadikan Aktif?" : "Kembalikan ke Bayangan?"}
      message={
        toActive
          ? `Setelah Aktif, absen dari ${device.name} dihitung sebagai absensi karyawan yang sudah dicocokkan. Pastikan karyawan sudah dicocokkan dan data uji terlihat benar. Mode ini bisa dikembalikan.`
          : `Setelah kembali ke Bayangan, ${device.name} hanya mencatat data dan tidak lagi dihitung sebagai absensi. Absensi yang sudah terbentuk tidak dihapus.`
      }
      confirmLabel={toActive ? "Ya, jadikan Aktif" : "Ya, kembalikan"}
      busy={update.isPending}
      error={error}
      onConfirm={confirm}
      onClose={onClose}
    />
  );
}

export function DeviceDeleteDialog({ device, onClose }: { device: Perangkat; onClose: () => void }) {
  const remove = useDeleteDevice();
  const [error, setError] = useState<string | null>(null);
  const confirm = async () => {
    setError(null);
    try {
      await remove.mutateAsync(device.device_id);
      toast.success("Mesin absensi dihapus.");
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Mesin belum bisa dihapus. Coba lagi."));
    }
  };
  return (
    <ConfirmDialog
      open
      title="Hapus mesin absensi"
      message={`Hapus ${device.name}? Data dari mesin ini tidak akan diterima lagi.`}
      confirmLabel="Hapus"
      danger
      busy={remove.isPending}
      error={error}
      onConfirm={confirm}
      onClose={onClose}
    />
  );
}

/** Menerapkan pemetaan ke data lama; bila masih ada sisa, pengguna bisa menjalankan lagi. */
export function ApplyOldEventsDialog({ onConfirm, busy, error, onClose }: {
  onConfirm: () => void;
  busy: boolean;
  error: string | null;
  onClose: () => void;
}) {
  return (
    <ConfirmDialog
      open
      title="Terapkan ke data lama?"
      message="Data lama dari mesin yang belum punya karyawan akan dicocokkan memakai pemetaan sekarang. Ini bisa mengubah catatan absensi yang sudah ada. Lanjutkan?"
      confirmLabel="Ya, terapkan"
      busy={busy}
      error={error}
      onConfirm={onConfirm}
      onClose={onClose}
    />
  );
}

/** Buat tautan penerima baru; tautan lama langsung tidak berlaku. */
export function RenewLinkDialog({ device, onDone, onClose }: {
  device: Perangkat;
  onDone: (link: TokenBaru) => void;
  onClose: () => void;
}) {
  const renew = useRenewReceiver();
  const [error, setError] = useState<string | null>(null);
  const confirm = async () => {
    setError(null);
    try {
      onDone(await renew.mutateAsync(device.device_id));
    } catch (err) {
      setError(errorMessage(err, "Tautan belum bisa dibuat. Coba lagi."));
    }
  };
  return (
    <ConfirmDialog
      open
      title="Buat tautan penerima baru?"
      message={`Tautan lama untuk ${device.name} tidak berlaku lagi. Tautan baru harus dipasang ulang di mesin, dan hanya ditampilkan satu kali.`}
      confirmLabel="Buat tautan"
      busy={renew.isPending}
      error={error}
      onConfirm={confirm}
      onClose={onClose}
    />
  );
}
