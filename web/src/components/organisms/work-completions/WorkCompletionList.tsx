import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ActionButton } from "@/components/molecules/ActionButton";
import { PHASE_COLOR, PHASE_LABEL, PHASES, phaseColor, phaseLabel, type Phase } from "@/lib/workPhase";
import { WorkCompletionAddButton } from "./WorkCompletionAddButton";
import { WorkCompletionDetailModal } from "./WorkCompletionDetailModal";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import {
  type WorkCompletion,
  type WorkCompletionListResponse,
  useUpdateWorkCompletionStatus,
  useDeleteWorkCompletion,
} from "@/services/workCompletionService";

/** Status pekerjaan klien → label sehari-hari + warna (berjalan biru, mendesak merah, menunggu kuning, selesai hijau). */
const STATUS: Record<string, { label: string; tone: string; bar: string }> = {
  ONGOING: { label: "Sedang dikerjakan", tone: "bg-info-bg text-info border-info-border", bar: "bg-info-solid" },
  URGENT: { label: "Mendesak", tone: "bg-danger-bg text-danger border-danger-border", bar: "bg-danger-solid" },
  PENDING: { label: "Menunggu klien", tone: "bg-warning-bg text-warning border-warning-border", bar: "bg-warning-solid" },
  PENDING_CLIENT: { label: "Menunggu klien", tone: "bg-warning-bg text-warning border-warning-border", bar: "bg-warning-solid" },
  COMPLETED: { label: "Selesai & diserahkan", tone: "bg-success-bg text-success border-success-border", bar: "bg-success-solid" },
};
const statusOf = (s: string) =>
  STATUS[s] ?? { label: "Belum mulai", tone: "bg-neutral-100 text-neutral-700 border-neutral-300", bar: "bg-neutral-400" };

const VIEWS = [
  { key: "open", label: "Masih berjalan" },
  { key: "done", label: "Sudah selesai" },
  { key: "all", label: "Semua" },
] as const;
type View = (typeof VIEWS)[number]["key"];

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
  const [picked, setView] = useState<View | null>(null);
  const [only, setOnly] = useState<Phase | null>(null);
  const updateStatusMutation = useUpdateWorkCompletionStatus();
  const deleteMutation = useDeleteWorkCompletion();

  const [deleteTarget, setDeleteTarget] = useState<WorkCompletion | null>(null);

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget.completion_id);
      toast.success("Pekerjaan klien berhasil dihapus.");
      setDeleteTarget(null);
    } catch {
      toast.error("Gagal menghapus pekerjaan klien.");
    }
  };

  const toggleUrgent = async (order: WorkCompletion) => {
    const next = order.order_status === "URGENT" ? "ONGOING" : "URGENT";
    try {
      await updateStatusMutation.mutateAsync({ id: order.completion_id, status: next });
      toast.success(next === "URGENT" ? "Ditandai mendesak." : "Tanda mendesak dihapus.");
    } catch {
      toast.error("Gagal mengubah status. Coba lagi.");
    }
  };

  const all = Array.isArray(query.data) ? query.data : [];
  // Bawaan: yang masih berjalan; bila tidak ada, tampilkan semua.
  const view: View = picked ?? (all.some((o) => o.order_status !== "COMPLETED") ? "open" : "all");
  const items = all.filter(
    (o) =>
      (view === "all" || (view === "done") === (o.order_status === "COMPLETED")) &&
      (!only || (o.phases ?? []).includes(only)),
  );
  const count = (v: View) => all.filter((o) => v === "all" || (v === "done") === (o.order_status === "COMPLETED")).length;

  return (
    <QueryState
      query={query}
      errorText="Daftar pekerjaan klien tidak dapat dimuat."
      empty={all.length === 0}
      emptyText="Belum ada pekerjaan klien."
      emptyAction={canManage && <WorkCompletionAddButton onAdd={onAdd} />}
    >
      {/* Saringan: keadaan + jenis pekerjaan */}
      <div className="mb-4 flex flex-col gap-3 rounded-panel border border-line bg-surface p-3 shadow-card">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Keadaan pekerjaan">
          {VIEWS.map((v) => (
            <ActionButton
              key={v.key}
              size="sm"
              role="tab"
              aria-selected={view === v.key}
              variant={view === v.key ? "default" : "outline"}
              onClick={() => setView(v.key)}
            >
              {`${v.label} (${count(v.key)})`}
            </ActionButton>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Jenis pekerjaan">
          <ActionButton size="sm" className="rounded-full" variant={only === null ? "default" : "outline"} onClick={() => setOnly(null)}>
            Semua jenis
          </ActionButton>
          {PHASES.map((ph) => (
            <ActionButton
              key={ph}
              size="sm"
              variant="outline"
              className={`rounded-full border ${PHASE_COLOR[ph].chip} ${only === ph ? "ring-2 ring-ink" : only ? "opacity-50" : ""}`}
              onClick={() => setOnly(only === ph ? null : ph)}
            >
              <TextBlock as="span" className={`mr-1.5 inline-block h-2.5 w-2.5 rounded-full ${PHASE_COLOR[ph].dot}`} />
              {PHASE_LABEL[ph]}
            </ActionButton>
          ))}
        </div>
      </div>

      {items.length === 0 ? (
        <TextBlock className="rounded-panel border border-dashed border-line p-8 text-center text-mist">
          Tidak ada pekerjaan klien untuk saringan ini.
        </TextBlock>
      ) : (
        <ListBlock className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((order: WorkCompletion) => {
            const st = statusOf(order.order_status);
            const pct = order.order_status === "COMPLETED" ? 100 : (order.progress_pct ?? 0);
            const main = (order.phases ?? [])[0];
            const done = order.order_status === "COMPLETED";
            return (
              <ListEntry key={order.completion_id}>
                <div
                  className={`relative flex h-full flex-col gap-3 overflow-hidden rounded-panel border border-line bg-surface p-4 pl-5 shadow-card transition-shadow hover:shadow-md`}
                >
                  <TextBlock as="span" className={`absolute inset-y-0 left-0 w-1.5 ${main ? phaseColor(main).bar : "bg-neutral-300"}`} />
                  <div className="flex items-start justify-between gap-2">
                    <TextBlock as="span" className="text-xs font-semibold uppercase tracking-wide text-mist">
                      {order.client_name}
                    </TextBlock>
                    <TextBlock as="span" className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-semibold ${st.tone}`}>
                      {st.label}
                    </TextBlock>
                  </div>

                  <TextBlock className="line-clamp-2 text-base font-semibold text-ink">{order.project_title}</TextBlock>

                  <div className="flex flex-wrap gap-1">
                    {(order.phases ?? []).map((ph) => (
                      <TextBlock key={ph} as="span" className={`rounded-full border px-2 py-0.5 text-xs font-medium ${phaseColor(ph).chip}`}>
                        {phaseLabel(ph)}
                      </TextBlock>
                    ))}
                  </div>

                  <div>
                    <div className="mb-1 flex justify-between text-xs">
                      <TextBlock as="span" className="text-mist">Kemajuan</TextBlock>
                      <TextBlock as="span" className="font-semibold text-ink">{`${pct}%`}</TextBlock>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-line">
                      <div className={`h-full rounded-full transition-all duration-700 ${st.bar}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>

                  <div className="space-y-0.5 text-xs text-mist">
                    {order.site_address && <TextBlock className="line-clamp-1">{`Lokasi: ${order.site_address}`}</TextBlock>}
                    {order.order_number && <TextBlock>{`No. surat perintah kerja: ${order.order_number}`}</TextBlock>}
                    {order.division_name && <TextBlock>{order.division_name}</TextBlock>}
                  </div>

                  <div className="mt-auto flex flex-wrap gap-2 border-t border-line/60 pt-3">
                    <ActionButton
                      size="sm"
                      className="flex-1 justify-center"
                      onClick={() => setSelectedCompletionId(order.completion_id)}
                    >
                      {done ? "Lihat hasil & dokumen" : "Buka detail"}
                    </ActionButton>
                    {canManage && !done && (
                      <>
                        <ActionButton size="sm" variant="outline" onClick={() => void toggleUrgent(order)}>
                        {order.order_status === "URGENT" ? "Hapus tanda mendesak" : "Tandai mendesak"}
                      </ActionButton>
                      <ActionButton
                        size="sm"
                        variant="ghost"
                        className="text-danger hover:bg-danger-bg hover:text-danger"
                        onClick={() => setDeleteTarget(order)}
                      >
                        Hapus
                      </ActionButton>
                    </>
                    )}
                  </div>
                </div>
              </ListEntry>
            );
          })}
        </ListBlock>
      )}

      <WorkCompletionDetailModal
        completionId={selectedCompletionId}
        onClose={() => setSelectedCompletionId(null)}
        canManage={canManage}
      />

      {deleteTarget && (
        <VmsDialog
          open
          title="Hapus pekerjaan klien"
          onClose={() => setDeleteTarget(null)}
          footer={
            <div className="flex justify-end gap-2">
              <ActionButton variant="outline" size="sm" onClick={() => setDeleteTarget(null)}>
                Batal
              </ActionButton>
              <ActionButton
                variant="default"
                size="sm"
                className="bg-danger text-white hover:bg-danger/90"
                disabled={deleteMutation.isPending}
                onClick={confirmDelete}
              >
                Hapus
              </ActionButton>
            </div>
          }
        >
          <TextBlock className="text-sm text-mist">
            Apakah Anda yakin ingin menghapus pekerjaan klien <TextBlock as="strong">{deleteTarget.project_title}</TextBlock>?
          </TextBlock>
        </VmsDialog>
      )}
    </QueryState>
  );
}
