import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextAreaField } from "@/components/molecules/Field";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadMoreBar } from "@/components/organisms/LoadMoreBar";
import type { KeysetMore } from "@/hooks/useKeysetList";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { overtimeActions } from "@/lib/aksiPeran";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { AttachmentButton } from "@/components/organisms/AttachmentButton";
import { type Overtime, useReviewOvertime } from "@/services/overtimeService";

/** Antrean lembur yang menunggu keputusan. Tombol hanya bila API menandai `can_review` (PM/OM divisi jadwal atau admin).
 * Penolakan wajib beralasan. */
export function OvertimeReviewList({ query, more }: { query: UseQueryResult<Overtime[]>; more: KeysetMore }) {
  const review = useReviewOvertime();
  const [rejecting, setRejecting] = useState<Overtime | null>(null);
  const [note, setNote] = useState("");
  const [noteError, setNoteError] = useState<string | null>(null);
  const rows = query.data ?? [];

  const approve = async (row: Overtime) => {
    try {
      await review.mutateAsync({ id: row.id, decision: "APPROVED" });
      toast.success(`Lembur ${row.employee_name} disetujui.`);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const closeReject = () => {
    setRejecting(null);
    setNote("");
    setNoteError(null);
  };

  const reject = async () => {
    if (!rejecting) return;
    const alasan = note.trim();
    if (!alasan) {
      setNoteError("Alasan penolakan wajib diisi.");
      return;
    }
    try {
      await review.mutateAsync({ id: rejecting.id, decision: "REJECTED", note: alasan });
      toast.success(`Lembur ${rejecting.employee_name} ditolak.`);
      closeReject();
    } catch (err) {
      setNoteError(errorMessage(err));
    }
  };

  return (
    <section className="mb-6 space-y-3">
      <TextBlock as="h2" className="font-semibold text-ink">
        Menunggu keputusan
      </TextBlock>
      <QueryState
        query={query}
        errorText="Antrean lembur tidak dapat dimuat."
        empty={rows.length === 0}
        emptyText="Tidak ada lembur yang menunggu keputusan."
      >
        <ListBlock className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((r) => {
            const actions = overtimeActions(r.status, r.can_review);
            return (
              <ListEntry key={r.id} className="space-y-2 rounded-panel border border-line bg-surface p-4 shadow-card">
                <TextBlock className="font-medium">{r.employee_name}</TextBlock>
                <TextBlock className="text-sm text-mist">
                  {formatDate(r.work_date)} · {r.hours} jam
                </TextBlock>
                <TextBlock className="rounded-control bg-hover p-2 text-xs">Alasan: {r.reason}</TextBlock>
                <AttachmentButton kind="overtime" parentId={r.id} locked={r.status !== "PENDING_PM"} />
                {actions.length > 0 && (
                  <div className="flex gap-2 pt-1">
                    <ActionButton
                      size="sm"
                      disabled={review.isPending}
                      onClick={() => approve(r)}
                      aria-label={`Setujui lembur ${r.employee_name}`}
                    >
                      Setujui
                    </ActionButton>
                    <ActionButton
                      size="sm"
                      variant="outline"
                      className="text-danger"
                      disabled={review.isPending}
                      onClick={() => setRejecting(r)}
                      aria-label={`Tolak lembur ${r.employee_name}`}
                    >
                      Tolak
                    </ActionButton>
                  </div>
                )}
              </ListEntry>
            );
          })}
        </ListBlock>
        <LoadMoreBar more={more} />
      </QueryState>
      {rejecting && (
        <VmsDialog
          open
          title="Tolak lembur"
          onClose={closeReject}
          footer={
            <div className="flex w-full items-center justify-end gap-2">
              <ActionButton variant="outline" onClick={closeReject} disabled={review.isPending}>
                Batal
              </ActionButton>
              <ActionButton variant="destructive" onClick={reject} pending={review.isPending} pendingText="Memproses…">
                {"Tolak lembur"}
              </ActionButton>
            </div>
          }
        >
          <TextAreaField
            label={`Alasan penolakan lembur ${rejecting.employee_name}`}
            rows={3}
            maxLength={1000}
            value={note}
            error={noteError ?? undefined}
            onChange={(e) => {
              setNote(e.target.value);
              setNoteError(null);
            }}
          />
        </VmsDialog>
      )}
    </section>
  );
}
