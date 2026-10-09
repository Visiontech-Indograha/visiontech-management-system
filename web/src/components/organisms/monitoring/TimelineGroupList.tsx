import type { UseQueryResult } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Badge } from "@/components/atoms/Badge";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate } from "@/lib/format";
import type { StatusTone } from "@/lib/labels";
import type { TimelineGroup } from "@/services/monitoringService";

/** Label & warna keadaan hari — prototype/js/operations.js dayState. */
const DAY_STATE: Record<string, [string, StatusTone]> = {
  APPROVED: ["Selesai & disetujui", "success"],
  SUBMITTED: ["Menunggu review PM", "warning"],
  CHANGES_REQUESTED: ["Perlu perbaikan", "danger"],
  LATE: ["Laporan belum dikirim", "danger"],
  TODAY: ["Dikerjakan hari ini", "info"],
  UPCOMING: ["Belum mulai", "neutral"],
};

/** Rencana kerja berjalan per pekerjaan + keadaan tiap hari, dengan keadaan memuat/galat/kosong. */
export function TimelineGroupList({ query }: { query: UseQueryResult<TimelineGroup[]> }) {
  return (
    <QueryState
      query={query}
      errorText="Timeline tidak dapat dimuat."
      empty={query.data?.length === 0}
      emptyText="Tidak ada pekerjaan berjalan pada rentang ini."
    >
      <div className="space-y-4">
        {query.data?.map((g) => (
          <section key={g.id} aria-label={g.title} className="rounded-panel border border-line bg-surface shadow-card p-4">
            <header className="mb-3 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <Link to={`/work-plans/${g.id}`} className="font-medium text-lens hover:underline">
                  {g.title}
                </Link>
                <p className="text-sm text-mist">
                  {g.number ?? "Belum terbit"} · {g.location_text ?? "-"} · Ketua: {g.leader?.full_name ?? "-"}
                </p>
                <p className="text-sm text-mist">
                  {formatDate(g.period_start)} – {formatDate(g.period_end)}
                </p>
              </div>
              <StatusBadge status={g.status} />
            </header>
            <p className="mb-3 text-sm">
              {g.approved_days}/{g.total_days} hari disetujui
              {g.late_days > 0 && <span className="text-danger"> · {g.late_days} laporan terlambat</span>}
            </p>
            {g.days.length === 0 ? (
              <p className="text-sm text-mist">Belum ada rincian harian pada rentang ini.</p>
            ) : (
              <ul className="divide-y divide-line">
                {g.days.map((d) => {
                  const [label, tone] = DAY_STATE[d.state] ?? [d.state, "neutral"];
                  return (
                    <li key={d.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                      <div>
                        <strong>{formatDate(d.work_date)}</strong>
                        <div className="text-mist">{d.title}</div>
                      </div>
                      <Badge tone={tone}>{label}</Badge>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        ))}
      </div>
    </QueryState>
  );
}
