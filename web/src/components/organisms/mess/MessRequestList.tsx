import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { pagedView, type ListControls } from "@/hooks/usePagedList";
import type { Paged } from "@/lib/paged";
import type { UseQueryResult } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextAreaField } from "@/components/molecules/Field";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { type MessStay, useDecideMessStay } from "@/services/messService";

/** Pengajuan hunian yang menunggu: PM divisi / OM / HR menyetujui atau menolak (penolakan wajib beralasan). */
export function MessRequestList({
  controls, requests,
}: {
  controls: ListControls;
  requests: UseQueryResult<Paged<MessStay>>;
}) {
  const decide = useDecideMessStay();
  const [approving, setApproving] = useState<MessStay | null>(null);
  const [rejecting, setRejecting] = useState<MessStay | null>(null);
  const [note, setNote] = useState("");
  const [noteError, setNoteError] = useState<string | null>(null);

  const approve = async () => {
    if (!approving) return;
    try {
      await decide.mutateAsync({ id: approving.mess_stay_id, approve: true });
      toast.success(`Pengajuan ${approving.employee_name} disetujui.`);
    } catch (err) {
      toast.error(errorMessage(err));
    }
    setApproving(null);
  };

  const reject = async () => {
    if (!rejecting) return;
    if (note.trim().length < 3) {
      setNoteError("Alasan penolakan wajib diisi.");
      return;
    }
    try {
      await decide.mutateAsync({
        id: rejecting.mess_stay_id,
        approve: false,
        note: note.trim(),
      });
      toast.success(`Pengajuan ${rejecting.employee_name} ditolak.`);
      setRejecting(null);
      setNote("");
      setNoteError(null);
    } catch (err) {
      setNoteError(errorMessage(err));
    }
  };

  const closeReject = () => {
    setRejecting(null);
    setNote("");
    setNoteError(null);
  };

  const view = pagedView(requests, controls);
  return (
    <>
      {requests.isPending && <LoadingBar className="h-24" />}
      {requests.isError && (
        <RetryNotice
          message="Pengajuan mess tidak dapat dimuat."
          onRetry={() => requests.refetch()}
        />
      )}
      {requests.data && requests.data.total === 0 && !view.active && (
        <div className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <TextBlock className="text-mist">
            Tidak ada pengajuan mess yang menunggu.
          </TextBlock>
        </div>
      )}
      {requests.data && (requests.data.total > 0 || view.active) && (
        <>
        <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari nama, NIP, atau mess..." active={view.active} onReset={view.reset} />
        {view.total === 0 && <TextBlock className="rounded-panel border border-line bg-surface p-6 text-center text-mist">Tidak ada yang cocok dengan pencarian.</TextBlock>}
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {view.rows.map((r) => (
            <ListEntry
              key={r.mess_stay_id}
              className="space-y-2 rounded-panel border border-line bg-surface p-4 shadow-card"
            >
              <TextBlock className="font-semibold text-ink">
                {r.employee_name}
              </TextBlock>
              <TextBlock className="text-sm">
                {r.mess_name} · {r.city}
              </TextBlock>
              <TextBlock className="text-xs text-mist">
                {formatDate(r.stay_start_date)} s/d{" "}
                {formatDate(r.stay_end_date)}
              </TextBlock>
              {r.request_note && (
                <TextBlock className="rounded-control bg-hover p-2 text-xs">
                  Catatan: {r.request_note}
                </TextBlock>
              )}
              <div className="flex gap-2 pt-1">
                <ActionButton
                  size="sm"
                  onClick={() => setApproving(r)}
                  aria-label={`Setujui ${r.employee_name}`}
                >
                  Setujui
                </ActionButton>
                <ActionButton
                  size="sm"
                  variant="outline"
                  className="text-danger"
                  onClick={() => setRejecting(r)}
                  aria-label={`Tolak ${r.employee_name}`}
                >
                  Tolak
                </ActionButton>
              </div>
            </ListEntry>
          ))}
        </ListBlock>
        {view.total > 0 && <ListPagination total={view.total} noun="pengajuan" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
        </>
      )}
      <ConfirmDialog
        open={approving !== null}
        title="Setujui pengajuan mess?"
        message={
          approving
            ? `${approving.employee_name} akan menempati ${approving.mess_name}.`
            : ""
        }
        confirmLabel="Setujui"
        busy={decide.isPending}
        onConfirm={approve}
        onClose={() => setApproving(null)}
      />
      {rejecting && (
        <VmsDialog
          open
          title="Tolak pengajuan mess"
          onClose={closeReject}
          footer={
            <div className="flex w-full items-center justify-end gap-2">
              <ActionButton
                variant="outline"
                onClick={closeReject}
                disabled={decide.isPending}
              >
                Batal
              </ActionButton>
              <ActionButton
                variant="destructive"
                onClick={reject}
                pending={decide.isPending} pendingText="Memproses…"
              >
                {"Tolak pengajuan"}
              </ActionButton>
            </div>
          }
        >
          <TextAreaField
            label={`Alasan penolakan untuk ${rejecting.employee_name}`}
            rows={3}
            maxLength={500}
            value={note}
            error={noteError ?? undefined}
            onChange={(e) => {
              setNote(e.target.value);
              setNoteError(null);
            }}
          />
        </VmsDialog>
      )}
    </>
  );
}
