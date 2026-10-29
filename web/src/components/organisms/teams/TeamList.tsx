import type { UseQueryResult } from "@tanstack/react-query";
import { ActionButton } from "@/components/molecules/ActionButton";
import { Trash2, User } from "@/components/molecules/Glyphs";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { pagedView, type ListControls } from "@/hooks/usePagedList";
import type { Paged } from "@/lib/paged";
import type { Team } from "@/services/teamService";
import { TeamAddButton } from "./TeamAddButton";

/** Daftar tim lapangan: divisi, kantor, ketua, jumlah anggota; Detail = anggota + kontak. */
export function TeamList({ controls, teams, onAdd, onRemove, onSelectTeam }: {
  controls: ListControls;
  teams: UseQueryResult<Paged<Team>>;
  onAdd: () => void;
  onRemove: (team: Team) => void;
  onSelectTeam: (team: Team) => void;
}) {
  const view = pagedView(teams, controls);
  return (
    <>
      {teams.isPending && <LoadingBar />}
      {teams.isError && <RetryNotice message="Daftar tim tidak dapat dimuat." onRetry={() => teams.refetch()} />}
      {teams.data && teams.data.total === 0 && !view.active && (
        <div className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <TextBlock className="mb-3 text-mist">Belum ada tim lapangan yang terdaftar.</TextBlock>
          <TeamAddButton onAdd={onAdd} />
        </div>
      )}
      {teams.data && (teams.data.total > 0 || view.active) && (
        <>
        <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari nama tim, ketua, divisi, atau kantor..." active={view.active} onReset={view.reset} />
        {view.total === 0 && <TextBlock className="rounded-panel border border-line bg-surface p-6 text-center text-mist">Tidak ada tim yang cocok dengan pencarian.</TextBlock>}
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {view.rows.map((t) => (
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
        {view.total > 0 && <ListPagination total={view.total} noun="tim" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
        </>
      )}
    </>
  );
}
