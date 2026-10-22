import { useState } from "react";
import { TeamsTemplate } from "@/components/templates/teams/TeamsTemplate";
import { type Team, useTeams, useDeleteTeam } from "@/services/teamService";

export function TeamsPage() {
  const teams = useTeams();
  const deleteTeam = useDeleteTeam();
  const [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState<Team | null>(null);

  return (
    <TeamsTemplate
      teams={teams}
      adding={adding}
      selected={selected}
      onAdd={() => setAdding(true)}
      onRemove={(team) => void deleteTeam.mutateAsync(team.team_id)}
      onSelect={setSelected}
      onCloseAdd={() => setAdding(false)}
    />
  );
}
