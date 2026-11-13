import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { useState } from "react";
import { toast } from "sonner";
import { errorMessage } from "@/lib/errors";
import { useDeleteMapping, type Pemetaan } from "@/services/hikvisionService";
import { ApplyOldEventsDialog } from "./DeviceConfirmDialogs";
import { MappingAutoDialog } from "./MappingAutoDialog";
import { MappingEditDialog } from "./MappingEditDialog";

export type Sub = { kind: "add" } | { kind: "edit"; m: Pemetaan } | { kind: "delete"; m: Pemetaan } | { kind: "auto" } | { kind: "apply" } | null;

/** Dialog turunan dari daftar pemetaan (tambah, ubah, hapus, otomatis, terapkan). */
export function MappingSubDialogs({ deviceId, sub, error, busy, onClose, onApply }: {
  deviceId: string;
  sub: Sub;
  error: string | null;
  busy: boolean;
  onClose: () => void;
  onApply: () => void;
}) {
  const remove = useDeleteMapping(deviceId);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const doDelete = async (m: Pemetaan) => {
    setDeleteError(null);
    try {
      await remove.mutateAsync(m.map_id);
      toast.success("Pemetaan dihapus.");
      onClose();
    } catch (err) {
      setDeleteError(errorMessage(err, "Pemetaan belum bisa dihapus. Coba lagi."));
    }
  };
  if (!sub) return null;
  switch (sub.kind) {
    case "add":
      return <MappingEditDialog deviceId={deviceId} onClose={onClose} />;
    case "edit":
      return <MappingEditDialog deviceId={deviceId} mapping={sub.m} onClose={onClose} />;
    case "auto":
      return <MappingAutoDialog deviceId={deviceId} onClose={onClose} />;
    case "apply":
      return <ApplyOldEventsDialog onConfirm={onApply} busy={busy} error={error} onClose={onClose} />;
    case "delete":
      return (
        <ConfirmDialog
          open
          danger
          title="Hapus pemetaan"
          message={`Hapus pemetaan ${sub.m.employee_no_string} untuk ${sub.m.full_name}? Absen berikutnya dari nomor ini tidak dikenali.`}
          confirmLabel="Hapus"
          busy={remove.isPending}
          error={deleteError}
          onConfirm={() => doDelete(sub.m)}
          onClose={onClose}
        />
      );
  }
}
