import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Antrean HR: permohonan yang sudah disetujui atasan dan menunggu persetujuan akhir HR. */
export function LeaveHrQueueCard({ count, onShow, active }: { count: number; onShow: () => void; active: boolean }) {
  return (
    <div className="flex flex-col gap-3 rounded-panel border border-sky-500/30 bg-sky-500/5 p-4 md:flex-row md:items-center md:justify-between">
      <div>
        <TextBlock className="font-semibold text-ink">Antrean HR</TextBlock>
        <TextBlock as="p" className="text-sm text-mist">
          {count > 0
            ? `${count} permohonan sudah disetujui atasan dan menunggu persetujuan akhir dari HR.`
            : "Belum ada permohonan yang menunggu persetujuan akhir dari HR."}
        </TextBlock>
      </div>
      {count > 0 && (
        <ActionButton variant="outline" disabled={active} onClick={onShow}>
          {active ? "Sedang ditampilkan" : "Tampilkan antrean HR"}
        </ActionButton>
      )}
    </div>
  );
}
