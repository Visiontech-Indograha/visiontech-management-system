import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ActionButton } from "@/components/molecules/ActionButton";
import { WorkCompletionAddButton } from "./WorkCompletionAddButton";
import { WorkCompletionDetailModal } from "./WorkCompletionDetailModal";
import {
  type WorkCompletion,
  type WorkCompletionListResponse,
  useUpdateWorkCompletionStatus,
} from "@/services/workCompletionService";

export function WorkCompletionList({
  query,
  canManage,
  onAdd,
}: {
  query: UseQueryResult<WorkCompletionListResponse>;
  canManage: boolean;
  onAdd: () => void;
}) {
  const [selectedCompletionId, setSelectedCompletionId] = useState<string | null>(null);
  const updateStatusMutation = useUpdateWorkCompletionStatus();

  const handleStatusChange = async (completionId: string, status: string) => {
    try {
      await updateStatusMutation.mutateAsync({
        id: completionId,
        status: status,
      });
      toast.success(`Status order berhasil diubah ke ${status}`);
    } catch {
      toast.error("Gagal memperbarui status order");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "URGENT":
        return <TextBlock as="span" className="rounded bg-rose-500/15 px-2 py-0.5 text-xs font-semibold text-rose-600">MENDESAK / URGENT</TextBlock>;
      case "ONGOING":
        return <TextBlock as="span" className="rounded bg-blue-500/15 px-2 py-0.5 text-xs font-semibold text-blue-600">BERJALAN / ONGOING</TextBlock>;
      case "PENDING_CLIENT":
      case "PENDING":
        return <TextBlock as="span" className="rounded bg-amber-500/15 px-2 py-0.5 text-xs font-semibold text-amber-600">MENUNGGU KLIEN</TextBlock>;
      case "COMPLETED":
        return <TextBlock as="span" className="rounded bg-emerald-500/15 px-2 py-0.5 text-xs font-semibold text-emerald-600">SELESAI (BAST)</TextBlock>;
      default:
        return <TextBlock as="span" className="rounded bg-slate-500/15 px-2 py-0.5 text-xs font-semibold text-slate-600">{status}</TextBlock>;
    }
  };

  const items = Array.isArray(query.data) ? query.data : [];

  return (
    <QueryState
      query={query}
      errorText="Daftar order proyek klien tidak dapat dimuat."
      empty={items.length === 0}
      emptyText="Belum ada order proyek klien yang terdaftar."
      emptyAction={canManage && <WorkCompletionAddButton onAdd={onAdd} />}
    >
      <ListBlock className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {items.map((order: WorkCompletion) => {
          const completedUnit = order.completed_unit ?? 0;
          const progressPercent = Math.min(
            100,
            Math.round((completedUnit / Math.max(1, order.total_target_unit)) * 100)
          );

          return (
            <ListEntry key={order.completion_id}>
              <div className="flex h-full flex-col justify-between rounded-panel border border-line bg-surface p-4 shadow-card">
                <div>
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <TextBlock as="span" className="text-xs font-bold uppercase tracking-wider text-primary">
                      {order.client_name}
                    </TextBlock>
                    {getStatusBadge(order.order_status)}
                  </div>

                  <TextBlock className="mb-1 text-base font-semibold text-ink line-clamp-2">
                    {order.project_title}
                  </TextBlock>

                  {order.order_number && (
                    <TextBlock className="mb-3 text-xs text-mist">
                      No. SPK/PO: {order.order_number}
                    </TextBlock>
                  )}

                  {/* Volume Target & Progress Bar */}
                  <div className="my-3 rounded-control bg-slate-50 p-2.5 dark:bg-slate-900/50">
                    <div className="mb-1.5 flex items-center justify-between text-xs font-medium">
                      <TextBlock as="span" className="text-mist">Target Realisasi</TextBlock>
                      <TextBlock as="span" className="font-bold text-ink">
                        {completedUnit} / {order.total_target_unit} {order.unit_measure}
                      </TextBlock>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                      <div
                        className={`h-full transition-all duration-300 ${
                          progressPercent >= 100 ? "bg-emerald-500" : "bg-primary"
                        }`}
                        style={{ width: `${progressPercent}%` }}
                      />
                    </div>
                  </div>

                  {order.site_address && (
                    <TextBlock className="text-xs text-mist line-clamp-1">
                      Lokasi: {order.site_address}
                    </TextBlock>
                  )}

                  {/* Kelola BoM & BAST Action */}
                  <div className="mt-3 pt-3 border-t border-line/60">
                    <ActionButton
                      variant="default"
                      size="sm"
                      onClick={() => setSelectedCompletionId(order.completion_id)}
                      className="w-full justify-center"
                    >
                      Kelola BoM & BAST
                    </ActionButton>
                  </div>
                </div>

                {/* PM Status Override Controls */}
                {canManage && (
                  <div className="mt-3 border-t border-line/60 pt-2.5">
                    <TextBlock className="mb-1.5 text-2xs font-semibold uppercase tracking-wider text-mist">
                      Kontrol Status PM (Override)
                    </TextBlock>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {order.order_status !== "ONGOING" && (
                        <ActionButton
                          variant="secondary"
                          size="sm"
                          onClick={() => handleStatusChange(order.completion_id, "ONGOING")}
                        >
                          Mulai Kerja
                        </ActionButton>
                      )}
                      {order.order_status !== "URGENT" && (
                        <ActionButton
                          variant="secondary"
                          size="sm"
                          onClick={() => handleStatusChange(order.completion_id, "URGENT")}
                        >
                          Tandai Mendesak
                        </ActionButton>
                      )}
                      {order.order_status !== "COMPLETED" && (
                        <ActionButton
                          variant="secondary"
                          size="sm"
                          onClick={() => handleStatusChange(order.completion_id, "COMPLETED")}
                        >
                          Selesaikan (BAST)
                        </ActionButton>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </ListEntry>
          );
        })}
      </ListBlock>

      <WorkCompletionDetailModal
        completionId={selectedCompletionId}
        onClose={() => setSelectedCompletionId(null)}
        canManage={canManage}
      />
    </QueryState>
  );
}
