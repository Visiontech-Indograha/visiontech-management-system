import type { UseQueryResult } from "@tanstack/react-query";
import { ActionButton } from "@/components/molecules/ActionButton";
import { InlineLink } from "@/components/molecules/Links";
import { Pill } from "@/components/molecules/Pill";
import { QueryState } from "@/components/molecules/QueryState";
import {
  TableBlock,
  TableBlockBody,
  TableBlockCell,
  TableBlockHead,
  TableBlockHeaderCell,
  TableBlockRow,
} from "@/components/molecules/TableBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDate } from "@/lib/format";
import { SURVEY_STATE_LABEL, type SurveyListItem, type SurveyState } from "@/services/surveyService";

const FILTERS: { state: SurveyState | undefined; label: string }[] = [
  { state: "SUBMITTED", label: "Menunggu tinjauan" },
  { state: "DRAFT", label: "Sedang diisi" },
  { state: "APPROVED", label: "Disetujui" },
  { state: undefined, label: "Semua" },
];

const TONE: Record<SurveyState, "warning" | "info" | "success"> = {
  SUBMITTED: "warning",
  DRAFT: "info",
  APPROVED: "success",
};

/** Daftar survei ACS/CCTV per status — titik masuk PM untuk meninjau, mengunduh laporan, dan merencanakan. */
export function SurveyList({ query, state, onState }: {
  query: UseQueryResult<SurveyListItem[]>;
  state: SurveyState | undefined;
  onState: (s: SurveyState | undefined) => void;
}) {
  const all = query.data ?? [];
  const rows = state ? all.filter((s) => s.state === state) : all;
  const count = (st: SurveyState | undefined) => (st ? all.filter((s) => s.state === st).length : all.length);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Saring status survei">
        {FILTERS.map((f) => (
          <ActionButton
            key={f.label}
            size="sm"
            variant={state === f.state ? "default" : "outline"}
            onClick={() => onState(f.state)}
          >
            {`${f.label} (${count(f.state)})`}
          </ActionButton>
        ))}
      </div>
      <QueryState
        query={query}
        errorText="Daftar survei tidak dapat dimuat."
        empty={rows.length === 0}
        emptyText={state === "SUBMITTED" ? "Tidak ada survei yang menunggu tinjauan." : "Belum ada survei."}
      >
        <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
          <TableBlock className="w-full text-left text-sm">
            <TableBlockHead className="border-b border-line text-mist">
              <TableBlockRow>
                <TableBlockHeaderCell className="px-4 py-3 font-medium">Survei</TableBlockHeaderCell>
                <TableBlockHeaderCell className="px-4 py-3 font-medium">Klien & lokasi</TableBlockHeaderCell>
                <TableBlockHeaderCell className="px-4 py-3 font-medium">Tim · tanggal</TableBlockHeaderCell>
                <TableBlockHeaderCell className="px-4 py-3 font-medium">Titik</TableBlockHeaderCell>
                <TableBlockHeaderCell className="px-4 py-3 font-medium">Status</TableBlockHeaderCell>
              </TableBlockRow>
            </TableBlockHead>
            <TableBlockBody>
              {rows.map((s) => (
                <TableBlockRow key={s.task_id} className={`border-b border-line last:border-0 hover:bg-hover ${s.state === "SUBMITTED" ? "bg-warning-bg/40" : ""}`}>
                  <TableBlockCell className="px-4 py-3">
                    <InlineLink to={`/surveys/${s.task_id}`} className="font-medium text-lens hover:underline">
                      {s.title}
                    </InlineLink>
                    <TextBlock className="text-xs text-mist">{`${s.format} · ${s.division_name}`}</TextBlock>
                  </TableBlockCell>
                  <TableBlockCell className="px-4 py-3">
                    <TextBlock>{s.client_name}</TextBlock>
                    <TextBlock className="text-xs text-mist">{s.site_address ?? s.project_title}</TextBlock>
                  </TableBlockCell>
                  <TableBlockCell className="px-4 py-3">
                    <TextBlock>{s.team_name ?? "-"}</TextBlock>
                    <TextBlock className="text-xs text-mist">{formatDate(s.work_date)}</TextBlock>
                  </TableBlockCell>
                  <TableBlockCell className="px-4 py-3">{s.point_count}</TableBlockCell>
                  <TableBlockCell className="px-4 py-3">
                    <Pill tone={TONE[s.state]}>{SURVEY_STATE_LABEL[s.state]}</Pill>
                  </TableBlockCell>
                </TableBlockRow>
              ))}
            </TableBlockBody>
          </TableBlock>
        </div>
      </QueryState>
    </div>
  );
}
