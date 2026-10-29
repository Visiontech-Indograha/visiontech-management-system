import type { UseQueryResult } from "@tanstack/react-query";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate } from "@/lib/format";
import type { DailyPlan } from "@/services/dailyPlanService";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/molecules/Panel";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { ArrowRight, MapPin } from "@/components/molecules/Glyphs";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

/** "Jadwal aktif": jadwal berjalan, hari ini, lalu yang menunggu persetujuan (maks. 6). */
export function HomeActivePlansCard({ plans, active }: { plans: UseQueryResult<DailyPlan[]>; active: DailyPlan[] }) {
  return (
    <Panel className="gap-4">
      <PanelHeader>
        <PanelTitle className="text-heading">Jadwal aktif minggu ini</PanelTitle>
        <PanelDescription>Jadwal berjalan, hari ini, dan yang menunggu persetujuan.</PanelDescription>
      </PanelHeader>
      <PanelContent className="px-3 md:px-4">
        {plans.isPending && <LoadingBar className="mx-3 h-14" />}
        {plans.isError && <TextBlock className="px-3 text-danger">Jadwal tidak dapat dimuat.</TextBlock>}
        {plans.isSuccess && active.length === 0 && <TextBlock className="px-3 text-mist">Belum ada jadwal aktif.</TextBlock>}
        <ListBlock className="divide-y divide-line">
          {active.map((p) => (
            <ListEntry key={p.daily_plan_id}>
              <InlineLink to="/work-plans" className="group flex items-center gap-4 rounded-control px-3 py-3 transition-colors hover:bg-hover">
                <div className="min-w-0 flex-1">
                  <TextBlock className="truncate font-medium text-ink">{p.team_name}</TextBlock>
                  <TextBlock className="mt-0.5 flex items-center gap-1.5 truncate text-body-sm text-mist">
                    <MapPin size={14} aria-hidden className="shrink-0" />
                    {p.site_name || "Lokasi belum ditentukan"} · {formatDate(p.work_date)}
                  </TextBlock>
                </div>
                <StatusBadge status={p.status} />
                <ArrowRight size={18} aria-hidden className="shrink-0 text-mist transition-transform duration-300 group-hover:translate-x-1" />
              </InlineLink>
            </ListEntry>
          ))}
        </ListBlock>
      </PanelContent>
    </Panel>
  );
}
