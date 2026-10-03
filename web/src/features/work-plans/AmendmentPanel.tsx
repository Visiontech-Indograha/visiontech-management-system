import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/ui/button";
import { TextAreaField } from "@/components/ui/Field";
import { Dialog } from "@/components/ui/VmsDialog";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import type { WorkPlan } from "./api";

type Change = components["schemas"]["PlanChangeOut"];
const changesKey = (planId: string) => ["plan-changes", planId] as const;

const TYPE_LABEL: Record<string, string> = { AMENDMENT: "Adendum", EXTEND: "Perpanjangan", PERSONNEL: "Adendum personel" };

/**
 * Usulan perubahan SK (alur SK v2 PR3, flowchart SK2-E): adendum yang diajukan ketua saat SK Berjalan.
 * PM menolak dengan catatan, atau menerima dengan mengubah isi SK (dokumen adendum + TTD PM → ketua menandatangani).
 */
export function AmendmentPanel({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const canManage = !!me?.permissions.includes("create:plan");
  const qc = useQueryClient();
  const changes = useQuery({
    queryKey: changesKey(plan.id),
    queryFn: async () => (await api.get<Change[]>(`/work-plans/${plan.id}/changes`)).data,
  });
  const [rejecting, setRejecting] = useState<Change | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const reject = useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) =>
      (await api.post(`/work-plans/${plan.id}/amendments/${id}/reject`, { reason })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: changesKey(plan.id) }),
  });
  const list = changes.data ?? [];
  if (list.length === 0) return null;

  return (
    <section aria-label="Usulan perubahan SK" className="rounded-panel border border-line bg-surface p-4 shadow-card">
      <h2 className="mb-3 text-base font-semibold">Usulan perubahan SK</h2>
      <ul className="space-y-3">
        {list.map((c) => (
          <li key={c.id} className="rounded-control border border-line p-3 text-sm">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="font-medium">{TYPE_LABEL[c.change_type] ?? c.change_type}</span>
              <StatusBadge status={c.status} />
            </div>
            <p className="whitespace-pre-line">{c.reason}</p>
            <p className="text-xs text-mist">
              {c.requested_by_name ?? "-"} · {formatDateTime(c.created_at)}
            </p>
            {c.decision_reason && <p className="mt-1 text-mist">Catatan PM: {c.decision_reason}</p>}
            {c.status === "AWAITING_LEADER_ACCEPTANCE" && (
              <p className="mt-1 text-warning">SK sudah diubah dan ditandatangani PM. Menunggu tanda tangan ketua di HP.</p>
            )}
            {canManage && c.change_type === "AMENDMENT" && c.status === "PENDING_PM" && plan.status === "IN_PROGRESS" && (
              <div className="mt-2 flex flex-col gap-2">
                <Button asChild>
                  <Link to={`/work-plans/${plan.id}/amend/${c.id}`}>Terima & ubah isi SK</Link>
                </Button>
                <Button variant="outline" onClick={() => (setRejecting(c), setNote(""), setError(null))}>
                  Tolak adendum
                </Button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {rejecting && (
        <Dialog
          open
          title="Tolak adendum"
          onClose={() => setRejecting(null)}
          footer={
            <>
              <Button variant="outline" onClick={() => setRejecting(null)} disabled={reject.isPending}>
                Batal
              </Button>
              <Button
                variant="destructive"
                disabled={reject.isPending}
                onClick={async () => {
                  if (!note.trim()) return setError("Catatan penolakan wajib diisi.");
                  try {
                    await reject.mutateAsync({ id: rejecting.id, reason: note.trim() });
                    toast.success("Adendum ditolak. Catatan dikirim ke ketua tim.");
                    setRejecting(null);
                  } catch (err) {
                    setError(errorMessage(err));
                  }
                }}
              >
                Tolak
              </Button>
            </>
          }
        >
          <TextAreaField label="Catatan untuk ketua tim" value={note} onChange={(e) => setNote(e.target.value)} error={error ?? undefined} />
        </Dialog>
      )}
    </section>
  );
}
