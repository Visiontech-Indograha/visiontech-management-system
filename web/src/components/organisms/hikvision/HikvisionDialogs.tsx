import type { Perangkat, TokenBaru } from "@/services/hikvisionService";
import { DeviceDeleteDialog, DeviceModeDialog, RenewLinkDialog } from "./DeviceConfirmDialogs";
import { DeviceFormDialog } from "./DeviceFormDialog";
import { MappingsDialog } from "./MappingsDialog";
import { ReceiverLinkDialog } from "./ReceiverLinkDialog";

export type HikDialog =
  | { kind: "add" }
  | { kind: "edit"; device: Perangkat }
  | { kind: "renew"; device: Perangkat }
  | { kind: "link"; device: Perangkat; link: TokenBaru }
  | { kind: "mappings"; device: Perangkat }
  | { kind: "mode"; device: Perangkat }
  | { kind: "remove"; device: Perangkat }
  | null;

/** Satu dialog aktif pada satu waktu. Tautan penerima hanya hidup di state ini dan hilang saat ditutup. */
export function HikvisionDialogs({ dialog, onDialog }: { dialog: HikDialog; onDialog: (d: HikDialog) => void }) {
  if (!dialog) return null;
  const close = () => onDialog(null);
  switch (dialog.kind) {
    case "add":
      return <DeviceFormDialog onClose={close} onCreated={(device, link) => onDialog({ kind: "link", device, link })} />;
    case "edit":
      return <DeviceFormDialog device={dialog.device} onClose={close} />;
    case "renew":
      return <RenewLinkDialog device={dialog.device} onClose={close} onDone={(link) => onDialog({ kind: "link", device: dialog.device, link })} />;
    case "link":
      return <ReceiverLinkDialog deviceName={dialog.device.name} link={dialog.link} onClose={close} />;
    case "mappings":
      return <MappingsDialog device={dialog.device} onClose={close} />;
    case "mode":
      return <DeviceModeDialog device={dialog.device} onClose={close} />;
    case "remove":
      return <DeviceDeleteDialog device={dialog.device} onClose={close} />;
  }
}
