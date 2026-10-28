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
import { MapPin } from "@/components/molecules/Glyphs";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { errorMessage } from "@/lib/errors";
import { type MessPlace, useDeleteMessPlace } from "@/services/messService";
import { MessPlaceFormDialog } from "./MessPlaceFormDialog";

/** Daftar mess (master): kartu dengan keterisian; HR/GA dapat menambah, mengubah, menghapus. */
export function MessPlaceList({
  controls, places,
  canManage,
  adding,
  onCloseAdd,
}: {
  controls: ListControls;
  places: UseQueryResult<Paged<MessPlace>>;
  canManage: boolean;
  adding: boolean;
  onCloseAdd: () => void;
}) {
  const [editing, setEditing] = useState<MessPlace | null>(null);
  const [deleting, setDeleting] = useState<MessPlace | null>(null);
  const remove = useDeleteMessPlace();

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await remove.mutateAsync(deleting.mess_id);
      toast.success(`${deleting.mess_name} dihapus dari daftar.`);
    } catch (err) {
      toast.error(errorMessage(err));
    }
    setDeleting(null);
  };

  const view = pagedView(places, controls);
  return (
    <>
      {places.isPending && <LoadingBar className="h-24" />}
      {places.isError && (
        <RetryNotice
          message="Daftar mess tidak dapat dimuat."
          onRetry={() => places.refetch()}
        />
      )}
      {places.data && places.data.total === 0 && !view.active && (
        <div className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <TextBlock className="text-mist">Belum ada mess terdaftar.</TextBlock>
        </div>
      )}
      {places.data && (places.data.total > 0 || view.active) && (
        <>
        <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari nama mess atau kota..." active={view.active} onReset={view.reset} />
        {view.total === 0 && <TextBlock className="rounded-panel border border-line bg-surface p-6 text-center text-mist">Tidak ada yang cocok dengan pencarian.</TextBlock>}
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {view.rows.map((p) => (
            <ListEntry
              key={p.mess_id}
              className="space-y-2 rounded-panel border border-line bg-surface p-4 shadow-card"
            >
              <div className="flex items-start justify-between gap-2">
                <TextBlock className="font-semibold text-ink">
                  {p.mess_name}
                </TextBlock>
                <TextBlock
                  as="span"
                  className="rounded-full bg-primary/10 px-2 py-0.5 text-2xs font-medium text-primary"
                >
                  {p.city}
                </TextBlock>
              </div>
              <div className="flex items-center gap-1 text-xs text-mist">
                <MapPin size={13} className="shrink-0" />
                <TextBlock as="span">{p.address}</TextBlock>
              </div>
              <TextBlock className="text-xs text-mist">
                Terisi hari ini: {p.occupied}
                {p.capacity
                  ? ` dari ${p.capacity} orang`
                  : " orang (kapasitas tak dibatasi)"}
              </TextBlock>
              {canManage && (
                <div className="flex gap-2 pt-1">
                  <ActionButton
                    variant="outline"
                    size="sm"
                    onClick={() => setEditing(p)}
                  >
                    Ubah
                  </ActionButton>
                  <ActionButton
                    variant="outline"
                    size="sm"
                    className="text-danger"
                    aria-label={`Hapus ${p.mess_name}`}
                    onClick={() => setDeleting(p)}
                  >
                    Hapus
                  </ActionButton>
                </div>
              )}
            </ListEntry>
          ))}
        </ListBlock>
        {view.total > 0 && <ListPagination total={view.total} noun="mess" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
        </>
      )}
      {adding && <MessPlaceFormDialog onClose={onCloseAdd} />}
      {editing && (
        <MessPlaceFormDialog place={editing} onClose={() => setEditing(null)} />
      )}
      <ConfirmDialog
        open={deleting !== null}
        danger
        title="Hapus mess dari daftar?"
        message={
          deleting
            ? `${deleting.mess_name} tidak lagi bisa dipilih. Riwayat hunian tetap tersimpan.`
            : ""
        }
        confirmLabel="Hapus"
        busy={remove.isPending}
        onConfirm={confirmDelete}
        onClose={() => setDeleting(null)}
      />
    </>
  );
}
