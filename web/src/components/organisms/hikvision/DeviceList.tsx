import type { UseQueryResult } from "@tanstack/react-query";
import { Pill as Badge } from "@/components/molecules/Pill";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import type { Perangkat } from "@/services/hikvisionService";
import { DeviceStatusLine } from "./DeviceStatusLine";
import { MODE_HINT, MODE_LABEL } from "./hikvisionLabels";

export interface DeviceActions {
  onAdd: () => void;
  onEdit: (d: Perangkat) => void;
  onLink: (d: Perangkat) => void;
  onMappings: (d: Perangkat) => void;
  onMode: (d: Perangkat) => void;
  onRemove: (d: Perangkat) => void;
}

/** Daftar mesin absensi per kantor: memuat, galat, kosong, dan berhasil. */
export function DeviceList({ devices, actions }: { devices: UseQueryResult<Perangkat[]>; actions: DeviceActions }) {
  if (devices.isPending)
    return (
      <div aria-hidden className="grid gap-3 md:grid-cols-2">
        <LoadingBar className="h-32" />
        <LoadingBar className="h-32" />
      </div>
    );
  if (devices.isError) return <RetryNotice message="Daftar mesin absensi belum bisa dimuat." onRetry={() => devices.refetch()} />;
  if (devices.data.length === 0)
    return (
      <div className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
        <TextBlock className="mb-3 text-mist">Belum ada mesin absensi. Tambahkan mesin agar absen dari mesin bisa dicatat.</TextBlock>
        <ActionButton onClick={actions.onAdd}>Tambah mesin</ActionButton>
      </div>
    );
  return (
    <ListBlock className="grid gap-3 md:grid-cols-2">
      {devices.data.map((d) => (
        <ListEntry key={d.device_id} className="space-y-3 rounded-panel border border-line bg-surface shadow-card p-4">
          <div className="min-w-0">
            <TextBlock className="break-words font-medium" title={d.name}>{d.name}</TextBlock>
            <TextBlock className="text-sm text-mist">{d.office_name} · {d.ip_address}:{d.http_port}</TextBlock>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <Badge tone={d.mode === "AKTIF" ? "success" : "info"}>{`Mode ${MODE_LABEL[d.mode]}`}</Badge>
              {!d.aktif && <Badge tone="neutral">Dimatikan</Badge>}
            </div>
            <TextBlock className="text-xs text-mist">{MODE_HINT[d.mode]}</TextBlock>
          </div>
          <DeviceStatusLine deviceId={d.device_id} />
          <div className="flex flex-wrap gap-2">
            <ActionButton variant="outline" size="sm" onClick={() => actions.onMappings(d)}>Cocokkan karyawan</ActionButton>
            <ActionButton variant="outline" size="sm" onClick={() => actions.onLink(d)}>Buat tautan penerima</ActionButton>
            <ActionButton variant="outline" size="sm" onClick={() => actions.onMode(d)}>
              {d.mode === "SHADOW" ? "Jadikan Aktif" : "Kembalikan ke Bayangan"}
            </ActionButton>
            <ActionButton variant="ghost" size="sm" onClick={() => actions.onEdit(d)} aria-label={`Ubah ${d.name}`}>Ubah</ActionButton>
            <ActionButton variant="ghost" size="sm" onClick={() => actions.onRemove(d)} aria-label={`Hapus ${d.name}`}>Hapus</ActionButton>
          </div>
        </ListEntry>
      ))}
    </ListBlock>
  );
}
