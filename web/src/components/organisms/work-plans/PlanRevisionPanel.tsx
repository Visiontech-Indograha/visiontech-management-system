import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { type WorkPlan, rejectRevisionRequest } from "@/services/workPlanService";
import { changesKey, usePlanChanges, type Change } from "@/services/planChangeService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { PlanRevisionRequestCard } from "@/components/organisms/work-plans/PlanRevisionRequestCard";

const TYPE_LABEL: Record<string, string> = { AMENDMENT: "Revisi", EXTEND: "Perpanjangan", PERSONNEL: "Revisi personel" };

/**
 * Usulan perubahan SK (alur SK v2 PR3, flowchart SK2-E): adendum yang diajukan ketua saat SK Berjalan.
 * PM menolak dengan catatan, atau menerima dengan mengubah isi SK (dokumen adendum + TTD PM → ketua menandatangani).
 */
export function PlanRevisionPanel({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const canManage = !!me?.permissions.includes("create:plan");
  const qc = useQueryClient();
  const changes = usePlanChanges(plan.id);
  const [rejecting, setRejecting] = useState<Change | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => rejectRevisionRequest(plan.id, id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: changesKey(plan.id) }),
  });
  const all = changes.data ?? [];
  const isPending = (c: Change) => c.change_type === "AMENDMENT" && c.status === "PENDING_PM";
  const pending = all.filter(isPending);
  const list = all.filter((c) => !isPending(c));
  const canAct = ["ACCEPTED", "IN_PROGRESS"].includes(plan.status);
  if (all.length === 0) return null;

  return (
    <>
      {pending.length > 0 && (
        <section aria-label="Permintaan revisi menunggu keputusan" className="space-y-3">
          {pending.map((c) => (
            <PlanRevisionRequestCard key={c.id} c={c}>
              {canManage ? (
                canAct && (
                  <div className="mt-3 flex flex-col gap-2">
                    <ActionButton asChild>
                      <InlineLink to={`/work-plans/${plan.id}/revise?change=${c.id}`}>Revisi rencana kerja (otomatis menyetujui)</InlineLink>
                    </ActionButton>
                    <ActionButton variant="outline" onClick={() => (setRejecting(c), setNote(""), setError(null))}>
                      Tolak permintaan
                    </ActionButton>
                  </div>
                )
              ) : (
                <TextBlock className="mt-2 text-sm font-medium text-ink">Menunggu keputusan PM.</TextBlock>
              )}
            </PlanRevisionRequestCard>
          ))}
        </section>
      )}
      {list.length > 0 && (
    <section aria-label="Permintaan revisi" className="rounded-panel border border-line bg-surface p-4 shadow-card">
      <TextBlock as="h2" className="mb-3 text-base font-semibold">Riwayat permintaan revisi</TextBlock>
      <ListBlock className="space-y-3">
        {list.map((c) => (
          <ListEntry key={c.id} className="rounded-control border border-line p-3 text-sm">
            <div className="mb-1 flex items-center justify-between gap-2">
              <TextBlock as="span" className="font-medium">{TYPE_LABEL[c.change_type] ?? c.change_type}</TextBlock>
              <StatusBadge status={c.status} />
            </div>
            <TextBlock className="whitespace-pre-line">{c.reason}</TextBlock>
            <TextBlock className="text-xs text-mist">
              {c.requested_by_name ?? "-"} · {formatDateTime(c.created_at)}
            </TextBlock>
            {c.decision_reason && <TextBlock className="mt-1 text-mist">Catatan PM: {c.decision_reason}</TextBlock>}
            {c.status === "AWAITING_LEADER_ACCEPTANCE" && (
              <TextBlock className="mt-1 text-warning">Rencana Kerja sudah diubah dan ditandatangani PM. Menunggu tanda tangan ketua di HP.</TextBlock>
            )}
          </ListEntry>
        ))}
      </ListBlock>
    </section>
      )}
      {rejecting && (
        <VmsDialog
          open
          title="Tolak permintaan"
          onClose={() => setRejecting(null)}
          footer={
            <>
              <ActionButton variant="outline" onClick={() => setRejecting(null)} disabled={reject.isPending}>
                Batal
              </ActionButton>
              <ActionButton
                variant="destructive"
                disabled={reject.isPending}
                onClick={async () => {
                  if (!note.trim()) return setError("Catatan penolakan wajib diisi.");
                  try {
                    await reject.mutateAsync({ id: rejecting.id, reason: note.trim() });
                    toast.success("Revisi ditolak. Catatan dikirim ke ketua tim.");
                    setRejecting(null);
                  } catch (err) {
                    setError(errorMessage(err));
                  }
                }}
              >
                Tolak
              </ActionButton>
            </>
          }
        >
          <TextAreaField label="Catatan untuk ketua tim" value={note} onChange={(e) => setNote(e.target.value)} error={error ?? undefined} />
        </VmsDialog>
      )}
    </>
  );
}
