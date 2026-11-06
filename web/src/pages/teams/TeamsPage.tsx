import { useState } from "react";
import { TeamsTemplate } from "@/components/templates/teams/TeamsTemplate";
import { useListControls } from "@/hooks/useListControls";
import { usePagedList } from "@/hooks/usePagedList";
import { useSession } from "@/stores/sessionStore";
import { type Team, useDeleteTeam } from "@/services/teamService";

export function TeamsPage() {
  const controls = useListControls({ prefix: "tim_" });
  const teams = usePagedList<Team>(["teams"], "/teams", controls);
  const canManage = (useSession().me?.permissions ?? []).includes("manage:teams");
  const deleteTeam = useDeleteTeam();
  const [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState<Team | null>(null);

  return (
    <TeamsTemplate
      controls={controls}
      teams={teams}
      canManage={canManage}
      adding={adding}
      selected={selected}
      onAdd={() => setAdding(true)}
      onRemove={(team) => void deleteTeam.mutateAsync(team.team_id)}
      onSelect={setSelected}
      onCloseAdd={() => setAdding(false)}
      isDeleting={deleteTeam.isPending}
    />
  );
}
