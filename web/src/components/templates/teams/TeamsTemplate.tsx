import type { UseQueryResult } from "@tanstack/react-query";
import { TeamAddButton } from "@/components/organisms/teams/TeamAddButton";
import { TeamDetailDialog } from "@/components/organisms/teams/TeamDetailDialog";
import { TeamFormDialog } from "@/components/organisms/teams/TeamFormDialog";
import { TeamList } from "@/components/organisms/teams/TeamList";
import type { Team } from "@/services/teamService";
import { PageTemplate } from "../PageTemplate";

export function TeamsTemplate({
  teams,
  adding,
  selected,
  onAdd,
  onRemove,
  onSelect,
  onCloseAdd,
}: {
  teams: UseQueryResult<Team[]>;
  adding: boolean;
  selected: Team | null;
  onAdd: () => void;
  onRemove: (team: Team) => void;
  onSelect: (team: Team | null) => void;
  onCloseAdd: () => void;
}) {
  return (
    <PageTemplate title="Tim Lapangan" action={<TeamAddButton onAdd={onAdd} />}>
      <TeamList teams={teams} onAdd={onAdd} onRemove={onRemove} onSelectTeam={onSelect} />
      {adding && <TeamFormDialog onClose={onCloseAdd} />}
      {selected && <TeamDetailDialog team={selected} onClose={() => onSelect(null)} />}
    </PageTemplate>
  );
}
