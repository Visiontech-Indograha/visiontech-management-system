import type { UseQueryResult } from "@tanstack/react-query";
import type { Team } from "@/services/teamService";
import { TeamAddButton } from "./TeamAddButton";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { User, Trash2 } from "@/components/molecules/Glyphs";

export function TeamList({
  teams,
  onAdd,
  onRemove,
  onSelectTeam,
}: {
  teams: UseQueryResult<Team[]>;
  onAdd: () => void;
  onRemove: (team: Team) => void;
  onSelectTeam?: (team: Team) => void;
}) {
  return (
    <>
      {teams.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <LoadingBar className="h-24" />
          <LoadingBar className="h-24" />
        </div>
      )}
      {teams.isError && (
        <RetryNotice message="Daftar tim tidak dapat dimuat." onRetry={() => teams.refetch()} />
      )}
      {teams.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
          <TextBlock className="mb-3 text-mist">Belum ada tim lapangan yang terdaftar.</TextBlock>
          <TeamAddButton onAdd={onAdd} />
        </div>
      )}
      {teams.data && teams.data.length > 0 && (
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {teams.data.map((t) => (
            <ListEntry key={t.id} className="flex items-start gap-3 rounded-panel border border-line bg-surface shadow-card p-4">
              <User className="mt-0.5 shrink-0 text-lens" size={20} aria-hidden />
              <div className="min-w-0 flex-1">
                <TextBlock className="font-medium text-ink">{t.name}</TextBlock>
                <TextBlock className="text-xs text-mist">
                  Leader: {t.leader_name || t.leader_id}
                </TextBlock>
                {t.description && (
                  <TextBlock className="text-sm text-mist">{t.description}</TextBlock>
                )}
                <TextBlock className="text-xs text-mist">
                  Anggota: {t.members?.length ?? 0} personil
                </TextBlock>
              </div>
              <div className="flex items-center gap-1">
                {onSelectTeam && (
                  <ActionButton variant="secondary" size="sm" onClick={() => onSelectTeam(t)}>
                    Detail
                  </ActionButton>
                )}
                <ActionButton variant="ghost" size="sm" onClick={() => onRemove(t)} aria-label={`Hapus ${t.name}`}>
                  <Trash2 size={16} />
                </ActionButton>
              </div>
            </ListEntry>
          ))}
        </ListBlock>
      )}
    </>
  );
}
