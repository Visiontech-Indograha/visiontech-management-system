import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { MappingSubDialogs, type Sub } from "./MappingSubDialogs";
import { errorMessage } from "@/lib/errors";
import { useApplyMappings, useMappings, type Perangkat } from "@/services/hikvisionService";

/** Pemetaan karyawan untuk satu mesin: daftar, tambah/ubah/hapus, cocokkan otomatis, terapkan ke data lama. */
export function MappingsDialog({ device, onClose }: { device: Perangkat; onClose: () => void }) {
  const id = device.device_id;
  const list = useMappings(id);
  const apply = useApplyMappings(id);
  const [sub, setSub] = useState<Sub>(null);
  const [error, setError] = useState<string | null>(null);
  const close = () => { setSub(null); setError(null); };

  const doApply = async () => {
    setError(null);
    try {
      const r = await apply.mutateAsync();
      toast.success(`${r.event_diperbarui} data lama diperbarui.${r.masih_ada_sisa ? " Masih ada sisa; terapkan lagi." : ""}`);
      if (!r.masih_ada_sisa) close();
    } catch (err) {
      setError(errorMessage(err, "Belum bisa menerapkan. Coba lagi."));
    }
  };

  return (
    <VmsDialog
      open
      size="lg"
      title={`Cocokkan karyawan: ${device.name}`}
      onClose={onClose}
      footer={<ActionButton variant="outline" onClick={onClose}>Tutup</ActionButton>}
    >
      <TextBlock className="mb-3 text-sm text-mist">
        Setiap karyawan punya nomor di mesin. Cocokkan nomor itu dengan karyawan agar absen dari mesin dikenali.
      </TextBlock>
      <div className="mb-4 flex flex-wrap gap-2">
        <ActionButton onClick={() => setSub({ kind: "add" })}>Tambah pemetaan</ActionButton>
        <ActionButton variant="outline" onClick={() => setSub({ kind: "auto" })}>Cocokkan otomatis</ActionButton>
        <ActionButton variant="outline" onClick={() => setSub({ kind: "apply" })}>Terapkan ke data lama</ActionButton>
      </div>
      {list.isPending && <LoadingBar aria-hidden className="h-24" />}
      {list.isError && <RetryNotice message="Daftar pemetaan belum bisa dimuat." onRetry={() => list.refetch()} />}
      {list.data?.length === 0 && (
        <TextBlock className="rounded-panel border border-line bg-surface p-4 text-center text-mist">
          Belum ada pemetaan. Coba Cocokkan otomatis atau tambah satu per satu.
        </TextBlock>
      )}
      {list.data && list.data.length > 0 && (
        <ListBlock className="divide-y divide-line">
          {list.data.map((m) => (
            <ListEntry key={m.map_id} className="flex items-center gap-2 py-2">
              <TextBlock className="min-w-0 flex-1 break-words text-sm">
                {m.employee_no_string} {"->"} {m.full_name} ({m.employee_no})
              </TextBlock>
              <ActionButton variant="ghost" size="sm" aria-label={`Ubah pemetaan ${m.employee_no_string}`} onClick={() => setSub({ kind: "edit", m })}>Ubah</ActionButton>
              <ActionButton variant="ghost" size="sm" aria-label={`Hapus pemetaan ${m.employee_no_string}`} onClick={() => setSub({ kind: "delete", m })}>Hapus</ActionButton>
            </ListEntry>
          ))}
        </ListBlock>
      )}
      <MappingSubDialogs deviceId={id} sub={sub} error={error} busy={apply.isPending} onClose={close} onApply={doApply} />
    </VmsDialog>
  );
}
