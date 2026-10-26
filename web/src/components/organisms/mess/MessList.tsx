import type { UseQueryResult } from "@tanstack/react-query";
import type { MessStay } from "@/services/messService";
import { MessAddButton } from "./MessAddButton";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { CalendarClock, LogOut, MapPin } from "@/components/molecules/Glyphs";

export function MessList({
  stays,
  onAdd,
  onCheckout,
}: {
  stays: UseQueryResult<MessStay[]>;
  onAdd: () => void;
  onCheckout: (stay: MessStay) => void;
}) {
  return (
    <>
      {stays.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <LoadingBar className="h-24" />
          <LoadingBar className="h-24" />
        </div>
      )}
      {stays.isError && (
        <RetryNotice message="Daftar hunian mess tidak dapat dimuat." onRetry={() => stays.refetch()} />
      )}
      {stays.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
          <TextBlock className="mb-3 text-mist">Belum ada karyawan yang tercatat tinggal di mess.</TextBlock>
          <MessAddButton onAdd={onAdd} />
        </div>
      )}
      {stays.data && stays.data.length > 0 && (
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {stays.data.map((s) => (
            <ListEntry
              key={s.mess_stay_id}
              className="flex items-start gap-3 rounded-panel border border-line bg-surface shadow-card p-4"
            >
              <CalendarClock className="mt-0.5 shrink-0 text-primary" size={20} aria-hidden />
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <TextBlock className="font-semibold text-ink">
                    {s.employee_name || `Karyawan (${s.employee_no || s.employee_id.slice(0, 8)})`}
                  </TextBlock>
                  <TextBlock as="span" className="rounded-full bg-primary/10 px-2 py-0.5 text-2xs font-medium text-primary">
                    {s.city}
                  </TextBlock>
                </div>
                <TextBlock className="text-xs text-ink font-medium">
                  {s.mess_name}
                </TextBlock>
                <div className="flex items-center gap-1 text-xs text-mist">
                  <MapPin size={13} className="shrink-0" />
                  <TextBlock as="span" className="line-clamp-1">{s.address}</TextBlock>
                </div>
                <TextBlock className="text-2xs text-mist">
                  Periode Inap: {s.stay_start_date} s/d {s.stay_end_date}
                </TextBlock>
              </div>
              <ActionButton
                variant="outline"
                size="sm"
                className="text-danger hover:bg-danger-bg hover:text-danger ml-2 shrink-0"
                onClick={() => onCheckout(s)}
              >
                <LogOut size={14} className="mr-1" />
                Selesai Inap
              </ActionButton>
            </ListEntry>
          ))}
        </ListBlock>
      )}
    </>
  );
}
