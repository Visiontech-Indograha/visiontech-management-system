import type { UseQueryResult } from "@tanstack/react-query";
import { ActionButton } from "@/components/molecules/ActionButton";
import { Trash2, User } from "@/components/molecules/Glyphs";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import type { Team } from "@/services/teamService";
import { TeamAddButton } from "./TeamAddButton";

/** Daftar tim lapangan: divisi, kantor, ketua, jumlah anggota; Detail = anggota + kontak. */
export function TeamList({ teams, onAdd, onRemove, onSelectTeam }: {
  teams: UseQueryResult<Team[]>;
  onAdd: () => void;
  onRemove: (team: Team) => void;
  onSelectTeam: (team: Team) => void;
}) {
  return (
    <>
      {teams.isPending && <LoadingBar />}
      {teams.isError && <RetryNotice message="Daftar tim tidak dapat dimuat." onRetry={() => teams.refetch()} />}
      {teams.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <TextBlock className="mb-3 text-mist">Belum ada tim lapangan yang terdaftar.</TextBlock>
          <TeamAddButton onAdd={onAdd} />
        </div>
      )}
      {teams.data && teams.data.length > 0 && (
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {teams.data.map((t) => (
            <ListEntry key={t.team_id} className="flex items-start gap-3 rounded-panel border border-line bg-surface p-4 shadow-card">
              <User className="mt-0.5 shrink-0 text-lens" size={20} aria-hidden />
              <div className="min-w-0 flex-1">
                <TextBlock className="font-medium text-ink">{t.name}</TextBlock>
                <TextBlock className="text-xs text-mist">{`${t.division_name ?? "-"} · ${t.office_name ?? "-"}`}</TextBlock>
                <TextBlock className="text-xs text-mist">{`Ketua: ${t.leader_name ?? "-"}`}</TextBlock>
                <TextBlock className="text-xs text-mist">{`Anggota: ${t.member_count} orang`}</TextBlock>
              </div>
              <div className="flex items-center gap-1">
                <ActionButton variant="secondary" size="sm" onClick={() => onSelectTeam(t)}>
                  Anggota & kontak
                </ActionButton>
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
