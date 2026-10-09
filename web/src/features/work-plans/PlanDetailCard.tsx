import { QueryState } from "@/components/molecules/QueryState";
import { formatDate } from "@/lib/format";
import { usePlanDetail, type WorkPlan } from "./api";
import { weekday } from "./weekday";

type Task = { title: string; description: string; files: { file_id: string; file_name: string }[] };
type Day = { work_date: string; tasks: Task[]; site_name?: string | null; work_type_name?: string | null; member_employee_ids?: string[] | null };
type Member = { employee_id: string; full_name: string; position: string; role_in_plan: string };
type Asset = { asset_id: string; kind: string; code: string; name: string; driver_name: string | null };

const th = "border-b border-line px-2 py-2 text-left font-semibold";
const td = "border-b border-line px-2 py-2 align-top";

/** Isi rencana kerja (format sama dengan dokumen PDF): tim + hari bertugas, alat & kendaraan, jadwal hari kerja. */
export function PlanDetailCard({ plan }: { plan: WorkPlan }) {
  const detail = usePlanDetail(plan.id);
  const d = detail.data;
  const p = (d?.plan ?? {}) as { work_type_name?: string | null; location_text?: string | null };
  const team = (d?.team ?? []) as Member[];
  const assets = (d?.assets ?? []) as Asset[];
  const days = (d?.days ?? []) as Day[];
  const leader = team.find((m) => m.role_in_plan === "LEADER")?.employee_id;
  const memberIds = team.filter((m) => m.role_in_plan === "MEMBER").map((m) => m.employee_id);
  const names = new Map(team.map((m) => [m.employee_id, m.full_name]));
  // Pekerja tiap hari (tanpa ketua): daftar khusus hari itu, atau seluruh anggota bila tanpa daftar.
  const workersOf = (day: Day) => (day.member_employee_ids ?? memberIds).filter((id) => id !== leader);
  const dutyDays = (id: string) => (id === leader ? days.length : days.filter((day) => workersOf(day).includes(id)).length);
  // Tanggal dalam rentang yang tidak punya hari kerja = hari libur.
  const holidays: string[] = [];
  for (let t = new Date(`${plan.period_start}T00:00:00Z`); t.toISOString().slice(0, 10) <= plan.period_end && holidays.length < 366; t.setUTCDate(t.getUTCDate() + 1)) {
    const iso = t.toISOString().slice(0, 10);
    if (!days.some((x) => x.work_date === iso)) holidays.push(iso);
  }
  return (
    <div className="mt-6 space-y-6">
      <QueryState query={detail} errorText="Isi rencana kerja tidak dapat dimuat.">
        <section aria-label="Tim" className="rounded-panel border border-line bg-surface p-4 shadow-card">
          <h2 className="mb-3 text-base font-semibold">Tim</h2>
          {team.length === 0 ? (
            <p className="text-sm text-mist">Belum ada tim.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] border-collapse text-sm">
                <thead className="bg-canvas">
                  <tr>
                    <th className={th}>Nama</th>
                    <th className={th}>Jabatan</th>
                    <th className={th}>Peran</th>
                    <th className={th}>Hari bertugas</th>
                  </tr>
                </thead>
                <tbody>
                  {team.map((m) => {
                    const n = dutyDays(m.employee_id);
                    return (
                      <tr key={m.employee_id}>
                        <td className={td}>{m.full_name}</td>
                        <td className={`${td} text-mist`}>{m.position || "-"}</td>
                        <td className={td}>{m.role_in_plan === "LEADER" ? "Ketua tim" : "Anggota"}</td>
                        <td className={td}>
                          {n === 0 ? <span className="text-mist">Belum dijadwalkan</span> : `${n} dari ${days.length} hari`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section aria-label="Alat & kendaraan" className="rounded-panel border border-line bg-surface p-4 shadow-card">
          <h2 className="mb-3 text-base font-semibold">Alat &amp; kendaraan</h2>
          {assets.length === 0 ? (
            <p className="text-sm text-mist">Tanpa alat atau kendaraan.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] border-collapse text-sm">
                <thead className="bg-canvas">
                  <tr>
                    <th className={th}>Jenis</th>
                    <th className={th}>Kode</th>
                    <th className={th}>Nama</th>
                    <th className={th}>Driver</th>
                  </tr>
                </thead>
                <tbody>
                  {assets.map((a) => (
                    <tr key={a.asset_id}>
                      <td className={td}>{a.kind === "VEHICLE" ? "Kendaraan" : "Alat"}</td>
                      <td className={td}>{a.code}</td>
                      <td className={td}>{a.name}</td>
                      <td className={td}>{a.driver_name ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section aria-label="Jadwal hari kerja" className="rounded-panel border border-line bg-surface p-4 shadow-card">
          <h2 className="mb-3 text-base font-semibold">Jadwal hari kerja</h2>
          {days.length === 0 ? (
            <p className="text-sm text-mist">Belum ada detail pekerjaan.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] border-collapse text-sm">
                <thead className="bg-canvas">
                  <tr>
                    <th className={`${th} w-10`}>No</th>
                    <th className={`${th} w-36`}>Hari, tanggal</th>
                    <th className={`${th} w-40`}>Jenis pekerjaan</th>
                    <th className={`${th} w-44`}>Lokasi</th>
                    <th className={th}>Detail pekerjaan</th>
                    <th className={`${th} w-48`}>Pekerja</th>
                  </tr>
                </thead>
                <tbody>
                  {days.map((day, i) => {
                    const workers = workersOf(day);
                    return (
                      <tr key={day.work_date}>
                        <td className={td}>{i + 1}</td>
                        <td className={td}>
                          <span className="font-medium">{weekday(day.work_date)}</span>
                          <span className="block text-mist">{formatDate(day.work_date)}</span>
                        </td>
                        <td className={td}>{day.work_type_name ?? p.work_type_name ?? "-"}</td>
                        <td className={td}>{day.site_name ?? p.location_text ?? plan.location_text ?? "-"}</td>
                        <td className={td}>
                          <ul className="space-y-1">
                            {day.tasks.map((t, j) => (
                              <li key={j}>
                                <span className="font-medium">{t.title}</span>
                                {t.description && <span className="text-mist"> — {t.description}</span>}
                                {t.files.length > 0 && <span className="block text-xs text-mist">Lampiran: {t.files.map((f) => f.file_name).join(", ")}</span>}
                              </li>
                            ))}
                          </ul>
                        </td>
                        <td className={td}>
                          {workers.length === 0 ? (
                            <span className="text-mist">Ketua saja</span>
                          ) : (
                            <ul>
                              {workers.map((id) => (
                                <li key={id}>{names.get(id) ?? id}</li>
                              ))}
                            </ul>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <p className="mt-2 text-xs text-mist">Ketua tim bertugas di semua hari kerja dan tidak diulang di kolom Pekerja.</p>
          {holidays.length > 0 && (
            <p className="mt-2 rounded-control border border-dashed border-line bg-canvas px-3 py-2 text-sm" aria-label="Hari libur">
              <span className="font-medium">Hari libur</span> (tidak wajib absen dan laporan):{" "}
              {holidays.map((h) => `${weekday(h)} ${formatDate(h)}`).join(", ")}
            </p>
          )}
        </section>
      </QueryState>
    </div>
  );
}
