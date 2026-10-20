import type { UseQueryResult } from "@tanstack/react-query";
import { ActionButton } from "@/components/molecules/ActionButton";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { addDays, type DailyPlan } from "@/services/dailyPlanService";

const DAY = new Intl.DateTimeFormat("id-ID", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });

export interface MatrixTeam {
  team_id: string;
  name: string;
  division_id: string;
}

/**
 * Matriks minggu: baris = tim, kolom = Senin–Minggu. Sel berisi jadwal tim pada tanggal itu (satu per tim per hari);
 * sel kosong bisa dipakai PM/OM untuk membuat jadwal baru.
 */
export function DailyWeekMatrix({ plans, teams, start, today, canPlan, onOpen, onCreate }: {
  plans: UseQueryResult<DailyPlan[]>;
  teams: MatrixTeam[];
  start: string;
  today: string;
  canPlan: boolean;
  onOpen: (plan: DailyPlan) => void;
  onCreate: (team: MatrixTeam, workDate: string) => void;
}) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i));
  const byCell = new Map((plans.data ?? []).map((p) => [`${p.team_id}|${p.work_date}`, p]));
  const rows = teams.length
    ? teams
    : [...new Map((plans.data ?? []).map((p) => [p.team_id, { team_id: p.team_id, name: p.team_name, division_id: p.division_id }])).values()];

  return (
    <QueryState query={plans} errorText="Jadwal tidak dapat dimuat." empty={rows.length === 0} emptyText="Belum ada jadwal minggu ini.">
      <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
        <TableBlock className="w-full min-w-[56rem] text-left text-sm">
          <TableBlockHead className="border-b border-line text-mist">
            <TableBlockRow>
              <TableBlockHeaderCell className="px-3 py-3 font-medium">Tim</TableBlockHeaderCell>
              {days.map((d) => (
                <TableBlockHeaderCell key={d} className={`px-2 py-3 font-medium ${d === today ? "text-ink" : ""}`}>
                  {DAY.format(new Date(`${d}T00:00:00Z`))}
                </TableBlockHeaderCell>
              ))}
            </TableBlockRow>
          </TableBlockHead>
          <TableBlockBody>
            {rows.map((team) => (
              <TableBlockRow key={team.team_id} className="border-b border-line align-top last:border-0">
                <TableBlockCell className="px-3 py-2 font-medium">{team.name}</TableBlockCell>
                {days.map((d) => {
                  const plan = byCell.get(`${team.team_id}|${d}`);
                  return (
                    <TableBlockCell key={d} className="px-2 py-2">
                      {plan ? (
                        <ActionButton
                          variant="outline"
                          size="sm"
                          className="flex h-auto w-full flex-col items-start gap-1 whitespace-normal py-2 text-left"
                          aria-label={`Jadwal ${team.name} ${d}`}
                          onClick={() => onOpen(plan)}
                        >
                          <StatusBadge status={plan.status} />
                          <TextBlock as="span" className="line-clamp-2 text-xs">{plan.site_name}</TextBlock>
                          <TextBlock as="span" className="text-xs text-mist">{plan.done_count}/{plan.item_count} item</TextBlock>
                        </ActionButton>
                      ) : canPlan && d >= today ? (
                        <ActionButton variant="ghost" size="sm" className="w-full text-mist" aria-label={`Buat jadwal ${team.name} ${d}`} onClick={() => onCreate(team, d)}>
                          + Jadwal
                        </ActionButton>
                      ) : (
                        <TextBlock as="span" className="text-xs text-mist">-</TextBlock>
                      )}
                    </TableBlockCell>
                  );
                })}
              </TableBlockRow>
            ))}
          </TableBlockBody>
        </TableBlock>
      </div>
    </QueryState>
  );
}
