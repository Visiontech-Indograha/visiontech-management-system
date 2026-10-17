import { QueryState } from "@/components/molecules/QueryState";
import { formatDate } from "@/lib/format";
import { usePlanDetail, type WorkPlan } from "@/services/workPlanService";
import { weekday } from "@/lib/weekday";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";
import { SectionTitle } from "@/components/molecules/SectionTitle";

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
          <SectionTitle>Tim</SectionTitle>
          {team.length === 0 ? (
            <TextBlock className="text-sm text-mist">Belum ada tim.</TextBlock>
          ) : (
            <div className="overflow-x-auto">
              <TableBlock className="w-full min-w-[520px] border-collapse text-sm">
                <TableBlockHead className="bg-canvas">
                  <TableBlockRow>
                    <TableBlockHeaderCell className={th}>Nama</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={th}>Jabatan</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={th}>Peran</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={th}>Hari bertugas</TableBlockHeaderCell>
                  </TableBlockRow>
                </TableBlockHead>
                <TableBlockBody>
                  {team.map((m) => {
                    const n = dutyDays(m.employee_id);
                    return (
                      <TableBlockRow key={m.employee_id}>
                        <TableBlockCell className={td}>{m.full_name}</TableBlockCell>
                        <TableBlockCell className={`${td} text-mist`}>{m.position || "-"}</TableBlockCell>
                        <TableBlockCell className={td}>{m.role_in_plan === "LEADER" ? "Ketua tim" : "Anggota"}</TableBlockCell>
                        <TableBlockCell className={td}>
                          {n === 0 ? <TextBlock as="span" className="text-mist">Belum dijadwalkan</TextBlock> : `${n} dari ${days.length} hari`}
                        </TableBlockCell>
                      </TableBlockRow>
                    );
                  })}
                </TableBlockBody>
              </TableBlock>
            </div>
          )}
        </section>

        <section aria-label="Alat & kendaraan" className="rounded-panel border border-line bg-surface p-4 shadow-card">
          <SectionTitle>Alat &amp; kendaraan</SectionTitle>
          {assets.length === 0 ? (
            <TextBlock className="text-sm text-mist">Tanpa alat atau kendaraan.</TextBlock>
          ) : (
            <div className="overflow-x-auto">
              <TableBlock className="w-full min-w-[480px] border-collapse text-sm">
                <TableBlockHead className="bg-canvas">
                  <TableBlockRow>
                    <TableBlockHeaderCell className={th}>Jenis</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={th}>Kode</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={th}>Nama</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={th}>Driver</TableBlockHeaderCell>
                  </TableBlockRow>
                </TableBlockHead>
                <TableBlockBody>
                  {assets.map((a) => (
                    <TableBlockRow key={a.asset_id}>
                      <TableBlockCell className={td}>{a.kind === "VEHICLE" ? "Kendaraan" : "Alat"}</TableBlockCell>
                      <TableBlockCell className={td}>{a.code}</TableBlockCell>
                      <TableBlockCell className={td}>{a.name}</TableBlockCell>
                      <TableBlockCell className={td}>{a.driver_name ?? "-"}</TableBlockCell>
                    </TableBlockRow>
                  ))}
                </TableBlockBody>
              </TableBlock>
            </div>
          )}
        </section>

        <section aria-label="Jadwal hari kerja" className="rounded-panel border border-line bg-surface p-4 shadow-card">
          <SectionTitle>Jadwal hari kerja</SectionTitle>
          {days.length === 0 ? (
            <TextBlock className="text-sm text-mist">Belum ada detail pekerjaan.</TextBlock>
          ) : (
            <div className="overflow-x-auto">
              <TableBlock className="w-full min-w-[860px] border-collapse text-sm">
                <TableBlockHead className="bg-canvas">
                  <TableBlockRow>
                    <TableBlockHeaderCell className={`${th} w-10`}>No</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={`${th} w-36`}>Hari, tanggal</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={`${th} w-40`}>Jenis pekerjaan</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={`${th} w-44`}>Lokasi</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={th}>Detail pekerjaan</TableBlockHeaderCell>
                    <TableBlockHeaderCell className={`${th} w-48`}>Pekerja</TableBlockHeaderCell>
                  </TableBlockRow>
                </TableBlockHead>
                <TableBlockBody>
                  {days.map((day, i) => {
                    const workers = workersOf(day);
                    return (
                      <TableBlockRow key={day.id ?? `${day.work_date}-${i}`}>
                        <TableBlockCell className={td}>{i + 1}</TableBlockCell>
                        <TableBlockCell className={td}>
                          <TextBlock as="span" className="font-medium">{weekday(day.work_date)}</TextBlock>
                          <TextBlock as="span" className="block text-mist">{formatDate(day.work_date)}</TextBlock>
                        </TableBlockCell>
                        <TableBlockCell className={td}>{day.work_type_name ?? p.work_type_name ?? "-"}</TableBlockCell>
                        <TableBlockCell className={td}>{day.site_name ?? p.location_text ?? plan.location_text ?? "-"}</TableBlockCell>
                        <TableBlockCell className={td}>
                          <ListBlock className="space-y-1">
                            {day.tasks.map((t, j) => (
                              <ListEntry key={j}>
                                <TextBlock as="span" className="font-medium">{t.title}</TextBlock>
                                {t.description && <TextBlock as="span" className="text-mist"> — {t.description}</TextBlock>}
                                {t.files.length > 0 && <TextBlock as="span" className="block text-xs text-mist">Lampiran: {t.files.map((f) => f.file_name).join(", ")}</TextBlock>}
                              </ListEntry>
                            ))}
                          </ListBlock>
                        </TableBlockCell>
                        <TableBlockCell className={td}>
                          {workers.length === 0 ? (
                            <TextBlock as="span" className="text-mist">Ketua saja</TextBlock>
                          ) : (
                            <ListBlock>
                              {workers.map((id) => (
                                <ListEntry key={id}>{names.get(id) ?? id}</ListEntry>
                              ))}
                            </ListBlock>
                          )}
                        </TableBlockCell>
                      </TableBlockRow>
                    );
                  })}
                </TableBlockBody>
              </TableBlock>
            </div>
          )}
          <TextBlock className="mt-2 text-xs text-mist">Ketua tim bertugas di semua hari kerja dan tidak diulang di kolom Pekerja.</TextBlock>
          {holidays.length > 0 && (
            <TextBlock className="mt-2 rounded-control border border-dashed border-line bg-canvas px-3 py-2 text-sm" aria-label="Hari libur">
              <TextBlock as="span" className="font-medium">Hari libur</TextBlock> (tidak wajib absen dan laporan):{" "}
              {holidays.map((h) => `${weekday(h)} ${formatDate(h)}`).join(", ")}
            </TextBlock>
          )}
        </section>
      </QueryState>
    </div>
  );
}
