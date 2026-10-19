import { useState } from "react";
import { TeamsTemplate } from "@/components/templates/teams/TeamsTemplate";
import { type Team, useTeams, useDeleteTeam } from "@/services/teamService";

export function TeamsPage() {
  const teams = useTeams();
  const deleteTeam = useDeleteTeam();
  const [adding, setAdding] = useState(false);

  const handleRemove = async (team: Team) => {
    const targetId = team.team_id || team.id;
    if (targetId) {
      await deleteTeam.mutateAsync(targetId);
    }
  };

  return (
    <TeamsTemplate
      teams={teams}
      adding={adding}
      onAdd={() => setAdding(true)}
      onRemove={handleRemove}
      onCloseAdd={() => setAdding(false)}
    />
  );
}
