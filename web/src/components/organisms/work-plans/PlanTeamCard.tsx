import { type WorkPlan } from "@/services/workPlanService";
import { usePlanTeam } from "@/services/reportService";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

const ROLE: Record<string, string> = { LEADER: "Ketua", MEMBER: "Anggota" };

/** Tim SK di halaman detail: dulu hanya ketua yang tampil (temuan R-19). */
export function PlanTeamCard({ plan }: { plan: WorkPlan }) {
  const team = usePlanTeam(plan.id);
  return (
    <section aria-label="Tim" className="mt-6 rounded-panel border border-line bg-surface shadow-card px-5 py-4">
      <TextBlock as="h2" className="mb-2 text-base font-semibold">Tim</TextBlock>
      {team.isPending && <LoadingBar className="h-10 w-full" />}
      {team.isError && <TextBlock className="text-sm text-danger">Tim tidak dapat dimuat.</TextBlock>}
      {team.data?.length === 0 && <TextBlock className="text-sm text-mist">Belum ada anggota tim.</TextBlock>}
      {!!team.data?.length && (
        <ListBlock className="divide-y divide-line text-sm">
          {team.data.map((m) => (
            <ListEntry key={m.employee_id} className="flex items-center justify-between gap-3 py-2">
              <TextBlock as="span">
                <TextBlock as="span" className="font-medium">{m.full_name}</TextBlock>
                {m.position && <TextBlock as="span" className="text-mist"> · {m.position}</TextBlock>}
              </TextBlock>
              <TextBlock as="span" className="rounded-full bg-hover px-2.5 py-0.5 text-xs font-medium">{ROLE[m.role_in_plan] ?? m.role_in_plan}</TextBlock>
            </ListEntry>
          ))}
        </ListBlock>
      )}
    </section>
  );
}
