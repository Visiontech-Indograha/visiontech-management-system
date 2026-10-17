import type { UseQueryResult } from "@tanstack/react-query";
import { TeamAddButton } from "@/components/organisms/teams/TeamAddButton";
import { TeamFormDialog } from "@/components/organisms/teams/TeamFormDialog";
import { TeamList } from "@/components/organisms/teams/TeamList";
import type { Team } from "@/services/teamService";
import { PageTemplate } from "../PageTemplate";

export function TeamsTemplate({
  teams,
  adding,
  onAdd,
  onRemove,
  onCloseAdd,
}: {
  teams: UseQueryResult<Team[]>;
  adding: boolean;
  onAdd: () => void;
  onRemove: (team: Team) => void;
  onCloseAdd: () => void;
}) {
  return (
    <PageTemplate title="Tim Lapangan" action={<TeamAddButton onAdd={onAdd} />}>
      <TeamList teams={teams} onAdd={onAdd} onRemove={onRemove} />
      {adding && <TeamFormDialog onClose={onCloseAdd} />}
    </PageTemplate>
  );
}
