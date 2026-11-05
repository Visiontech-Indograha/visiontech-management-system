import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { copyWeekTargets, summarizeBulk, type StandbyGroup, type WeeklyMatrix } from "@/lib/alokasi";
import { errorMessage } from "@/lib/errors";
import { useIdempotencyKey } from "@/lib/idempotency";
import { useBulkStandby, useCopyPlan } from "@/services/alokasiService";

/** "Siaga hari kosong": konfirmasi lalu POST bulk-standby per divisi (sel yang sudah terisi dilewati API). */
export function StandbyConfirmDialog({ groups, cellCount, onClose }: {
  groups: StandbyGroup[];
  cellCount: number;
  onClose: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const standby = useBulkStandby();
  const idem = useIdempotencyKey(JSON.stringify(groups));
  const confirm = async () => {
    setError(null);
    setBusy(true);
    let created = 0;
    let skipped = 0;
    try {
      for (const [i, g] of groups.entries()) {
        const s = summarizeBulk(await standby.mutateAsync({ ...g, idempotencyKey: idem.keyFor(i) }));
        created += s.created;
        skipped += s.skipped;
      }
      idem.renew();
      toast.success(`${created} siaga dibuat${skipped ? `, ${skipped} dilewati` : ""}.`);
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <VmsDialog open title="Siaga hari kosong?" onClose={onClose}
               footer={<><ActionButton variant="outline" onClick={onClose} disabled={busy}>Batal</ActionButton>
                 <ActionButton onClick={confirm} disabled={busy || cellCount === 0}>Buat siaga</ActionButton></>}>
      <TextBlock>
        {cellCount} sel kosong akan dibuat sebagai SIAGA (menunggu perintah PM). Sel yang sudah berisi dilewati otomatis.
      </TextBlock>
      {error && <TextBlock role="alert" className="mt-2 text-danger">{error}</TextBlock>}
    </VmsDialog>
  );
}

/** "Salin minggu ke minggu berikutnya": setiap jadwal minggu ini disalin ke +7 hari, berurutan. */
export function CopyWeekConfirmDialog({ matrix, onClose }: { matrix: WeeklyMatrix; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  const copy = useCopyPlan();
  const targets = copyWeekTargets(matrix);
  const confirm = async () => {
    setBusy(true);
    let ok = 0;
    let failed = 0;
    for (const t of targets) {
      try {
        await copy.mutateAsync({ id: t.daily_plan_id, work_dates: [t.work_date] });
        ok += 1;
      } catch {
        failed += 1;
      }
    }
    setBusy(false);
    toast[failed ? "error" : "success"](
      `${ok} jadwal disalin${failed ? `, ${failed} gagal (tanggal sudah terisi atau tidak valid)` : ""}.`,
    );
    onClose();
  };
  return (
    <VmsDialog open title="Salin minggu ke minggu berikutnya?" onClose={onClose}
               footer={<><ActionButton variant="outline" onClick={onClose} disabled={busy}>Batal</ActionButton>
                 <ActionButton onClick={confirm} disabled={busy || targets.length === 0}>
                   {busy ? "Menyalin..." : "Salin"}
                 </ActionButton></>}>
      <TextBlock>
        {targets.length
          ? `${targets.length} jadwal minggu ini disalin ke tanggal +7 hari sebagai draf.`
          : "Tidak ada jadwal minggu ini untuk disalin."}
      </TextBlock>
    </VmsDialog>
  );
}
