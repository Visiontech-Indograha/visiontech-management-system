import { ACTION_LABEL, AUDIT_ENTITIES } from "@/lib/auditLabels";

/** Label aksi; kode tak dikenal tampil apa adanya. */
export function actionLabel(code: string): string {
  return ACTION_LABEL[code] ?? code;
}

/** Label entitas; kode tak dikenal tampil apa adanya. */
export function entityLabel(code: string): string {
  return AUDIT_ENTITIES[code] ?? code;
}

export const FIELD_LABEL: Record<string, string> = {
  name: "Nama",
  full_name: "Nama lengkap",
  status: "Status",
  client_code: "Kode klien",
  site_name: "Nama lokasi",
  latitude: "Garis lintang",
  longitude: "Garis bujur",
  geofence_radius_meters: "Radius lokasi (meter)",
  radius_m: "Radius absen (meter)",
  city_boundary_radius_m: "Radius batas kota (meter)",
  clock_in_time: "Jam masuk",
  clock_out_time: "Jam pulang",
  in_city_meal_rate: "Uang makan dalam kota",
  out_city_meal_rate: "Uang makan luar kota",
  is_main_office: "Kantor utama",
  address: "Alamat",
  pic_name: "Nama penanggung jawab",
  pic_phone: "Telepon penanggung jawab",
  phone_number: "Nomor telepon",
  pkwt_end_date: "Akhir kontrak",
  photo_file_id: "Foto",
  employee_no: "Nomor karyawan",
  office_id: "Lokasi kerja",
  division_id: "Divisi",
  team_id: "Tim",
  position_id: "Jabatan",
  join_date: "Tanggal masuk",
  ownership_type: "Kepemilikan",
  category: "Kategori",
  tool_code: "Kode alat",
  vehicle_type: "Jenis kendaraan",
  number_plate: "Plat nomor",
};

export interface AuditChangeLine {
  label: string;
  text: string;
}

function show(v: unknown): string {
  if (v === null || v === undefined || v === "") return "kosong";
  if (v === true) return "ya";
  if (v === false) return "tidak";
  return typeof v === "object" ? JSON.stringify(v) : String(v);
}

/** Ubah JSON perubahan jadi baris "Bidang: lama -> baru"; bidang rahasia hanya ditandai diubah. */
export function describeChanges(changes: Record<string, unknown> | null | undefined): AuditChangeLine[] {
  if (!changes) return [];
  const lines: AuditChangeLine[] = [];
  const diff = changes.changes;
  if (diff && typeof diff === "object") {
    for (const [f, v] of Object.entries(diff as Record<string, { old?: unknown; new?: unknown }>)) {
      const e = v ?? {};
      const text = "old" in e && "new" in e ? `${show(e.old)} -> ${show(e.new)}` : "new" in e ? show(e.new) : show(e.old);
      lines.push({ label: FIELD_LABEL[f] ?? f, text });
    }
  }
  const masked = changes.masked_changed;
  if (Array.isArray(masked)) {
    for (const f of masked) lines.push({ label: FIELD_LABEL[String(f)] ?? String(f), text: "diubah (nilai disembunyikan)" });
  }
  for (const [k, v] of Object.entries(changes)) {
    if (k === "changes" || k === "masked_changed") continue;
    lines.push({ label: FIELD_LABEL[k] ?? k, text: show(v) });
  }
  return lines;
}

/** Terjemahkan kata cari berupa label aksi ke awalan kode yang dikenal API; selain itu apa adanya. */
export function resolveAuditSearch(q: string): string {
  const t = q.trim().toLowerCase();
  if (t.length < 3) return q;
  const codes = Object.entries(ACTION_LABEL)
    .filter(([c, l]) => l.toLowerCase().includes(t) && c.toLowerCase() !== t)
    .map(([c]) => c);
  if (codes.length === 0) return q;
  let pre = codes[0];
  for (const c of codes) while (!c.startsWith(pre)) pre = pre.slice(0, -1);
  return pre.length >= 3 ? pre : q;
}
