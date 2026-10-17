import type { UseQueryResult } from "@tanstack/react-query";
import type { MessStay } from "@/services/messService";
import { MessAddButton } from "./MessAddButton";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { CalendarClock, LogOut } from "@/components/molecules/Glyphs";

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
            <ListEntry key={s.id} className="flex items-start gap-3 rounded-panel border border-line bg-surface shadow-card p-4">
              <CalendarClock className="mt-0.5 shrink-0 text-lens" size={20} aria-hidden />
              <div className="min-w-0 flex-1">
                <TextBlock className="font-medium text-ink">
                  {s.employee_name || s.employee_id}
                </TextBlock>
                <TextBlock className="text-xs text-mist">
                  Mess: {s.mess_name} {s.room_number ? `· Kamar ${s.room_number}` : ""}
                </TextBlock>
                <TextBlock className="text-xs text-mist">
                  Masuk: {s.check_in_date} {s.check_out_date ? `· Keluar: ${s.check_out_date}` : ""}
                </TextBlock>
                <TextBlock className="text-xs font-medium text-ink">
                  Status: {s.status}
                </TextBlock>
                {s.notes && (
                  <TextBlock className="text-sm text-mist">{s.notes}</TextBlock>
                )}
              </div>
              {s.status === "ACTIVE" && (
                <ActionButton variant="outline" size="sm" onClick={() => onCheckout(s)}>
                  <LogOut size={16} />
                  Checkout
                </ActionButton>
              )}
            </ListEntry>
          ))}
        </ListBlock>
      )}
    </>
  );
}
