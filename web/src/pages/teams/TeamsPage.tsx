import { useState } from "react";
import { TeamsTemplate } from "@/components/templates/teams/TeamsTemplate";
import { type Team, useTeams, useDeleteTeam } from "@/services/teamService";

export function TeamsPage() {
  const teams = useTeams();
  const deleteTeam = useDeleteTeam();
  const [adding, setAdding] = useState(false);

  const handleRemove = async (team: Team) => {
    await deleteTeam.mutateAsync(team.id);
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
