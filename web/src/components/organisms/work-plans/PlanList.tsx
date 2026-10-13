import type { UseQueryResult } from "@tanstack/react-query";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate } from "@/lib/format";
import type { WorkPlan } from "@/services/workPlanService";
import { PlanArchivedCard } from "./PlanArchivedCard";
import { PlanCreateButton } from "./PlanCreateButton";
import { ActionButton } from "@/components/molecules/ActionButton";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

/** Kartu rencana kerja (atau draf terarsip) dengan keadaan memuat/galat/kosong. */
export function PlanList({ plans, archived, canManage, onCreate, onEdit }: {
  plans: UseQueryResult<WorkPlan[]>;
  archived: boolean;
  canManage: boolean;
  onCreate: () => void;
  /** Buka pratinjau draf untuk disunting. */
  onEdit: (plan: WorkPlan) => void;
}) {
  return (
      <QueryState
        query={plans}
        errorText="Daftar work plan tidak dapat dimuat."
        empty={plans.data?.length === 0}
        emptyText={archived ? "Tidak ada draf terarsip." : "Belum ada work plan yang dapat Anda lihat."}
        emptyAction={canManage && !archived && <PlanCreateButton onCreate={onCreate} />}
      >
        <ListBlock className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {plans.data?.map((p) => (
            <ListEntry key={p.id}>
              {archived ? (
                <PlanArchivedCard plan={p} />
              ) : (
              <div className="flex h-full flex-col rounded-panel border border-line bg-surface shadow-card">
              <InlineLink
                to={`/work-plans/${p.id}`}
                className="block flex-1 rounded-panel p-4 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <TextBlock as="span" className="font-medium text-lens">{p.title}</TextBlock>
                  <StatusBadge status={p.status} />
                </div>
                {p.is_out_of_town && (
                  <TextBlock className="mb-1 mr-1 inline-block rounded-control bg-accent px-2 py-0.5 text-sm font-medium text-lens">Luar kota</TextBlock>
                )}
                {p.pending_request && canManage && (
                  <TextBlock className="mb-1 inline-block rounded-control bg-warning-bg px-2 py-0.5 text-sm font-medium text-warning">
                    Perlu tindakan: ada permintaan revisi dari ketua
                  </TextBlock>
                )}
                <TextBlock className="text-sm text-mist">{p.number ?? "Nomor terbit saat rencana kerja diterbitkan"}</TextBlock>
                <TextBlock className="text-sm text-mist">{p.location_text}</TextBlock>
                <TextBlock className="text-sm text-mist">
                  {formatDate(p.period_start)} – {formatDate(p.period_end)}
                </TextBlock>
              </InlineLink>
              {canManage && p.status === "DRAFT" && (
                <div className="border-t border-line p-3">
                  <ActionButton variant="outline" className="w-full" onClick={() => onEdit(p)}>
                    Sunting rencana kerja
                  </ActionButton>
                </div>
              )}
              </div>
              )}
            </ListEntry>
          ))}
        </ListBlock>
      </QueryState>
  );
}
