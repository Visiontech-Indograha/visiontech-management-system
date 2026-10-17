import type { UseQueryResult } from "@tanstack/react-query";
import type { Offboarding } from "@/services/offboardingService";
import { OffboardingAddButton } from "./OffboardingAddButton";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { FileCheck2, FileWarning, ShieldCheck } from "@/components/molecules/Glyphs";

export function OffboardingList({
  offboardings,
  onAdd,
  onVerifyClearance,
  onDecision,
}: {
  offboardings: UseQueryResult<Offboarding[]>;
  onAdd: () => void;
  onVerifyClearance?: (itemId: string, isCleared: boolean) => void;
  onDecision?: (id: string, approved: boolean) => void;
}) {
  return (
    <>
      {offboardings.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <LoadingBar className="h-24" />
          <LoadingBar className="h-24" />
        </div>
      )}
      {offboardings.isError && (
        <RetryNotice message="Daftar offboarding tidak dapat dimuat." onRetry={() => offboardings.refetch()} />
      )}
      {offboardings.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
          <TextBlock className="mb-3 text-mist">Belum ada pengajuan offboarding atau clearance karyawan.</TextBlock>
          <OffboardingAddButton onAdd={onAdd} />
        </div>
      )}
      {offboardings.data && offboardings.data.length > 0 && (
        <ListBlock className="grid gap-4">
          {offboardings.data.map((o) => (
            <ListEntry key={o.id} className="rounded-panel border border-line bg-surface shadow-card p-4 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <TextBlock className="font-medium text-ink">
                    {o.employee_name || o.employee_id}
                  </TextBlock>
                  <TextBlock className="text-xs text-mist">
                    Tanggal Resign: {o.resignation_date} · Hari Kerja Terakhir: {o.last_working_date}
                  </TextBlock>
                  {o.reason && (
                    <TextBlock className="text-sm text-mist">Alasan: {o.reason}</TextBlock>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <TextBlock className="text-xs font-semibold px-2 py-0.5 rounded border border-line bg-surface-muted text-ink">
                    {o.status}
                  </TextBlock>
                  {o.status === "IN_CLEARANCE" && onDecision && (
                    <>
                      <ActionButton size="sm" variant="secondary" onClick={() => onDecision(o.id, true)}>
                        <ShieldCheck size={16} />
                        Setujui
                      </ActionButton>
                      <ActionButton size="sm" variant="ghost" onClick={() => onDecision(o.id, false)}>
                        Tolak
                      </ActionButton>
                    </>
                  )}
                </div>
              </div>

              {o.clearance_items && o.clearance_items.length > 0 && (
                <div className="border-t border-line pt-2">
                  <TextBlock className="text-xs font-medium text-mist mb-2">Item Clearance Aset & Serah Terima:</TextBlock>
                  <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
                    {o.clearance_items.map((item) => (
                      <div key={item.id} className="flex items-center justify-between p-2 rounded bg-surface-muted border border-line">
                        <div className="min-w-0">
                          <TextBlock className="text-xs font-medium text-ink">{item.item_name}</TextBlock>
                          <TextBlock className="text-[10px] text-mist">{item.category}</TextBlock>
                        </div>
                        <div className="flex items-center gap-1">
                          {item.is_cleared ? (
                            <FileCheck2 className="text-emerald-500" size={16} />
                          ) : (
                            <FileWarning className="text-amber-500" size={16} />
                          )}
                          {onVerifyClearance && !item.is_cleared && (
                            <ActionButton
                              variant="ghost"
                              size="sm"
                              onClick={() => onVerifyClearance(item.id, true)}
                              aria-label={`Verifikasi ${item.item_name}`}
                            >
                              Verifikasi
                            </ActionButton>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </ListEntry>
          ))}
        </ListBlock>
      )}
    </>
  );
}
