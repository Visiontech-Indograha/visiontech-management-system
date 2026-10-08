import { QueryState } from "@/components/molecules/QueryState";
import { formatDate } from "@/lib/format";
import { usePlanDetail, type WorkPlan } from "./api";

type Task = { title: string; description: string; files: { file_id: string; file_name: string }[] };
type Day = { work_date: string; tasks: Task[] };
type Member = { employee_id: string; full_name: string; position: string; role_in_plan: string };
type Asset = { asset_id: string; kind: string; code: string; name: string; driver_name: string | null };

/** Isi SK alur v2: tim, alat & kendaraan, detail pekerjaan per hari (GET /work-plans/{id}/detail). */
export function PlanDetailCard({ plan }: { plan: WorkPlan }) {
  const detail = usePlanDetail(plan.id);
  const d = detail.data;
  const team = (d?.team ?? []) as Member[];
  const assets = (d?.assets ?? []) as Asset[];
  const days = (d?.days ?? []) as Day[];
  return (
    <div className="mt-6 space-y-6">
      <QueryState query={detail} errorText="Isi rencana kerja tidak dapat dimuat.">
        <div className="grid gap-6 md:grid-cols-2">
          <section aria-label="Tim" className="rounded-panel border border-line bg-surface p-4 shadow-card">
            <h2 className="mb-3 text-base font-semibold">Tim</h2>
            {team.length === 0 ? (
              <p className="text-sm text-mist">Belum ada tim.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {team.map((m) => (
                  <li key={m.employee_id} className="flex justify-between gap-2">
                    <span>
                      {m.full_name} <span className="text-mist">— {m.position}</span>
                    </span>
                    <span className="shrink-0 text-mist">{m.role_in_plan === "LEADER" ? "Ketua tim" : "Anggota"}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <div className="rounded-panel border border-line bg-surface p-4 shadow-card">
            <h2 className="mb-3 text-base font-semibold">Alat &amp; kendaraan</h2>
            {assets.length === 0 ? (
              <p className="text-sm text-mist">Tanpa alat atau kendaraan.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {assets.map((a) => (
                  <li key={a.asset_id}>
                    {a.kind === "VEHICLE" ? "Kendaraan" : "Alat"}: {a.name} · {a.code}
                    {a.driver_name && <span className="block text-mist">Driver: {a.driver_name}</span>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <div className="rounded-panel border border-line bg-surface p-4 shadow-card">
          <h2 className="mb-3 text-base font-semibold">Detail pekerjaan per hari</h2>
          {days.length === 0 ? (
            <p className="text-sm text-mist">Belum ada detail pekerjaan.</p>
          ) : (
            <ol className="space-y-3">
              {days.map((day, i) => (
                <li key={day.work_date} className="rounded-control border border-line p-3">
                  <p className="mb-2 text-sm font-semibold">
                    Hari {i + 1} · {formatDate(day.work_date)}
                  </p>
                  <ul className="space-y-2 text-sm">
                    {day.tasks.map((t, j) => (
                      <li key={j}>
                        <span className="font-medium">{t.title}</span>
                        {t.description && <span className="text-mist"> — {t.description}</span>}
                        {t.files.length > 0 && <span className="block text-xs text-mist">Lampiran: {t.files.map((f) => f.file_name).join(", ")}</span>}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          )}
        </div>
      </QueryState>
    </div>
  );
}
