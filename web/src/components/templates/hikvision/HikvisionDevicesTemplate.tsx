import type { UseQueryResult } from "@tanstack/react-query";
import { DeviceAddButton } from "@/components/organisms/hikvision/DeviceAddButton";
import { DeviceList, type DeviceActions } from "@/components/organisms/hikvision/DeviceList";
import { HikvisionDialogs, type HikDialog } from "@/components/organisms/hikvision/HikvisionDialogs";
import type { Perangkat } from "@/services/hikvisionService";
import { PageTemplate } from "../PageTemplate";

export type { HikDialog };

/** Kerangka "Mesin absensi": daftar mesin per kantor + dialog tambah/ubah/tautan/pemetaan. */
export function HikvisionDevicesTemplate({ devices, actions, dialog, onDialog }: {
  devices: UseQueryResult<Perangkat[]>;
  actions: DeviceActions;
  dialog: HikDialog;
  onDialog: (d: HikDialog) => void;
}) {
  return (
    <PageTemplate
      title="Mesin absensi"
      description="Mesin absensi di kantor. Pasang tautan penerima di mesin, cocokkan karyawan, lalu jadikan Aktif."
      action={<DeviceAddButton onAdd={actions.onAdd} />}
    >
      <DeviceList devices={devices} actions={actions} />
      <HikvisionDialogs dialog={dialog} onDialog={onDialog} />
    </PageTemplate>
  );
}
