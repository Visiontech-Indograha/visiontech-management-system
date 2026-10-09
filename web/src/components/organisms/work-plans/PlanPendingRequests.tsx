import { usePlanChanges } from "@/services/planChangeService";
import { PendingRequestCard } from "./PlanRevisionPanel";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Permintaan revisi ketua yang masih menunggu: tampil di atas editor agar PM menjawabnya; menyimpan revisi = menyetujui. */
export function PlanPendingRequests({ planId }: { planId: string }) {
  const changes = usePlanChanges(planId);
  const pending = (changes.data ?? []).filter((c) => c.change_type === "AMENDMENT" && c.status === "PENDING_PM");
  if (pending.length === 0) return null;
  return (
    <div className="mb-4 space-y-3">
      {pending.map((c) => (
        <PendingRequestCard key={c.id} c={c}>
          <TextBlock className="mt-2 text-sm font-medium text-ink">Menyimpan revisi ini otomatis menyetujui permintaan di atas.</TextBlock>
        </PendingRequestCard>
      ))}
    </div>
  );
}
