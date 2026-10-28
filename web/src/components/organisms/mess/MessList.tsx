import type { UseQueryResult } from "@tanstack/react-query";
import { useState } from "react";
import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { pagedView, type ListControls } from "@/hooks/usePagedList";
import type { Paged } from "@/lib/paged";
import type { MessStay } from "@/services/messService";
import { MessAddButton } from "./MessAddButton";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { UserAvatar } from "@/components/organisms/UserAvatar";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { formatDate } from "@/lib/format";
import { wibDate } from "@/services/dailyPlanService";
import { LogOut, MapPin } from "@/components/molecules/Glyphs";

export function MessList({
  controls, stays,
  canAdd,
  onAdd,
  onCheckout,
}: {
  controls: ListControls;
  stays: UseQueryResult<Paged<MessStay>>;
  canAdd: boolean;
  onAdd: () => void;
  onCheckout: (stay: MessStay) => void;
}) {
  const [ending, setEnding] = useState<MessStay | null>(null);
  const view = pagedView(stays, controls);
  const today = wibDate();
  return (
    <>
      {stays.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <LoadingBar className="h-24" />
          <LoadingBar className="h-24" />
        </div>
      )}
      {stays.isError && (
        <RetryNotice
          message="Daftar hunian mess tidak dapat dimuat."
          onRetry={() => stays.refetch()}
        />
      )}
      {stays.data && stays.data.total === 0 && !view.active && (
        <div className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
          <TextBlock className="mb-3 text-mist">
            Belum ada karyawan yang tercatat tinggal di mess.
          </TextBlock>
          {canAdd && <MessAddButton onAdd={onAdd} />}
        </div>
      )}
      {stays.data && (stays.data.total > 0 || view.active) && (
        <>
        <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari nama, NIP, mess, atau kota..." active={view.active} onReset={view.reset} />
        {view.total === 0 && <TextBlock className="rounded-panel border border-line bg-surface p-6 text-center text-mist">Tidak ada hunian yang cocok dengan pencarian.</TextBlock>}
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {view.rows.map((s) => (
            <ListEntry
              key={s.mess_stay_id}
              className="flex items-start gap-3 rounded-panel border border-line bg-surface shadow-card p-4"
            >
              <UserAvatar name={s.employee_name} fileId={s.employee_photo_file_id} size="sm" />
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <TextBlock className="font-semibold text-ink">
                    {s.employee_name ||
                      `Karyawan (${s.employee_no || (s.employee_id ? s.employee_id.slice(0, 8) : "-")})`}
                  </TextBlock>
                  <TextBlock
                    as="span"
                    className="rounded-full bg-primary/10 px-2 py-0.5 text-2xs font-medium text-primary"
                  >
                    {s.city}
                  </TextBlock>
                </div>
                <TextBlock className="text-xs text-ink font-medium">
                  {s.mess_name}
                </TextBlock>
                <div className="flex items-center gap-1 text-xs text-mist">
                  <MapPin size={13} className="shrink-0" />
                  <TextBlock as="span" className="line-clamp-1">
                    {s.address}
                  </TextBlock>
                </div>
                <TextBlock className="text-2xs text-mist">
                  Periode inap: {formatDate(s.stay_start_date)} s/d{" "}
                  {formatDate(s.stay_end_date)}
                  {s.stay_start_date > today
                    ? " · Belum dimulai"
                    : s.stay_end_date < today
                      ? " · Sudah selesai"
                      : " · Sedang menginap"}
                </TextBlock>
              </div>
              {canAdd && s.stay_start_date <= today && s.stay_end_date >= today && (
                <ActionButton
                  variant="outline"
                  size="sm"
                  className="text-danger hover:bg-danger-bg hover:text-danger ml-2 shrink-0"
                  onClick={() => setEnding(s)}
                >
                  <LogOut size={14} className="mr-1" />
                  Selesai Inap
                </ActionButton>
              )}
            </ListEntry>
          ))}
        </ListBlock>
        {view.total > 0 && <ListPagination total={view.total} noun="hunian" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
        </>
      )}
      <ConfirmDialog
        open={ending !== null}
        title="Selesaikan inap?"
        message={
          ending
            ? `Inap ${ending.employee_name} di ${ending.mess_name} akan ditandai selesai.`
            : ""
        }
        confirmLabel="Selesai inap"
        onConfirm={() => {
          if (ending) onCheckout(ending);
          setEnding(null);
        }}
        onClose={() => setEnding(null)}
      />
    </>
  );
}
