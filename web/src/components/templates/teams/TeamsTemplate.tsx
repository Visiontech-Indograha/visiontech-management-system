import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { TeamAddButton } from "@/components/organisms/teams/TeamAddButton";
import { TeamDetailDialog } from "@/components/organisms/teams/TeamDetailDialog";
import { TeamFormDialog } from "@/components/organisms/teams/TeamFormDialog";
import { TeamList } from "@/components/organisms/teams/TeamList";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
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
  isDeleting = false,
}: {
  teams: UseQueryResult<Team[]>;
  adding: boolean;
  selected: Team | null;
  onAdd: () => void;
  onRemove: (team: Team) => void;
  onSelect: (team: Team | null) => void;
  onCloseAdd: () => void;
  isDeleting?: boolean;
}) {
  const [teamToDelete, setTeamToDelete] = useState<Team | null>(null);

  const confirmRemove = () => {
    if (!teamToDelete) return;
    onRemove(teamToDelete);
    setTeamToDelete(null);
  };

  return (
    <PageTemplate title="Tim Lapangan" action={<TeamAddButton onAdd={onAdd} />}>
      <TeamList teams={teams} onAdd={onAdd} onRemove={(team) => setTeamToDelete(team)} onSelectTeam={onSelect} />
      {adding && <TeamFormDialog onClose={onCloseAdd} />}
      {selected && <TeamDetailDialog team={selected} onClose={() => onSelect(null)} />}
      <ConfirmDialog
        open={teamToDelete !== null}
        title="Hapus Tim Lapangan?"
        message={`Apakah Anda yakin ingin menghapus tim "${teamToDelete?.name ?? ""}"? Tindakan ini tidak dapat dibatalkan.`}
        confirmLabel="Hapus Tim"
        danger
        busy={isDeleting}
        onConfirm={confirmRemove}
        onClose={() => setTeamToDelete(null)}
      />
    </PageTemplate>
  );
}
