import { useState } from "react";
import { HikvisionDevicesTemplate, type HikDialog } from "@/components/templates/hikvision/HikvisionDevicesTemplate";
import { useHikvisionDevices } from "@/services/hikvisionService";

/** Mesin absensi: GET/POST/PATCH/DELETE /hikvision/devices, izin manage:hikvision. */
export function HikvisionDevicesPage() {
  const devices = useHikvisionDevices();
  const [dialog, setDialog] = useState<HikDialog>(null);
  return (
    <HikvisionDevicesTemplate
      devices={devices}
      dialog={dialog}
      onDialog={setDialog}
      actions={{
        onAdd: () => setDialog({ kind: "add" }),
        onEdit: (device) => setDialog({ kind: "edit", device }),
        onLink: (device) => setDialog({ kind: "renew", device }),
        onMappings: (device) => setDialog({ kind: "mappings", device }),
        onMode: (device) => setDialog({ kind: "mode", device }),
        onRemove: (device) => setDialog({ kind: "remove", device }),
      }}
    />
  );
}
