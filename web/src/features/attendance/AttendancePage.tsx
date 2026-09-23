import { X } from "lucide-react";
import { useState } from "react";
import toast from "react-hot-toast";
import { useSession } from "@/app/session";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { ApiError } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";
import { ROLE_LABEL } from "@/lib/types";
import { downloadExport, FLAG_LABEL, useAttendanceList, useSelfie, type AttendanceItem } from "./api";
import { CorrectionDialog } from "./CorrectionDialog";

const inputCls = "h-10 rounded-control border border-line bg-surface px-3 text-sm";
const iso = (d: Date) => d.toISOString().slice(0, 10);

function Selfie({ id }: { id: string }) {
  const selfie = useSelfie(id);
  if (selfie.isError) return <p className="text-sm text-danger">Selfie tidak dapat dimuat.</p>;
  if (!selfie.data) return <div className="h-64 animate-pulse rounded-control bg-hover" aria-label="Memuat selfie" />;
  return <img src={selfie.data} alt="Selfie absen" className="max-h-72 rounded-control border border-line object-contain" />;
}

/** Panel geser: pratinjau selfie, peta, dan risk flags (docs/06-UI-UX §5). */
function DetailPanel({ item, onClose }: { item: AttendanceItem; onClose: () => void }) {
  return (
    <aside role="dialog" aria-label="Detail absensi" className="fixed inset-y-0 right-0 z-40 w-full max-w-md overflow-y-auto border-l border-line bg-surface p-5 shadow-overlay">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold">{item.full_name}</h2>
        <button type="button" aria-label="Tutup" onClick={onClose} className="rounded-control p-1 text-mist hover:bg-hover">
          <X size={20} />
        </button>
      </div>
      <dl className="mb-4 text-sm">
        <div className="flex justify-between border-b border-line py-2">
          <dt className="text-mist">Tanggal</dt>
          <dd className="font-medium">{formatDate(item.attendance_date)}</dd>
        </div>
        <div className="flex justify-between border-b border-line py-2">
          <dt className="text-mist">Waktu</dt>
          <dd className="font-medium">{item.is_manual ? "Koreksi manual" : formatDateTime(item.checked_in_at)}</dd>
        </div>
        <div className="flex justify-between border-b border-line py-2">
          <dt className="text-mist">Akurasi</dt>
          <dd className="font-medium">{item.accuracy_m != null ? `${item.accuracy_m} m` : "-"}</dd>
        </div>
        <div className="flex justify-between border-b border-line py-2">
          <dt className="text-mist">Sumber</dt>
          <dd className="font-medium">{item.source}</dd>
        </div>
        {item.manual_reason && (
          <div className="py-2">
            <dt className="text-mist">Alasan koreksi</dt>
            <dd className="font-medium">{item.manual_reason}</dd>
          </div>
        )}
      </dl>
      {item.risk_flags.length > 0 && (
        <ul className="mb-4 rounded-control bg-warning-soft px-3 py-2 text-sm text-warning">
          {item.risk_flags.map((f) => (
            <li key={f}>{FLAG_LABEL[f] ?? f}</li>
          ))}
        </ul>
      )}
      {item.map_url && (
        <a href={item.map_url} target="_blank" rel="noreferrer" className="mb-4 inline-block font-semibold text-lens hover:underline">
          Buka peta
        </a>
      )}
      {item.selfie_url ? <Selfie id={item.id} /> : <p className="text-sm text-mist">Tidak ada selfie (koreksi manual).</p>}
    </aside>
  );
}

/** mode "all": Finance/SA (ekspor); mode "team": TL (koreksi). */
export function AttendancePage({ mode }: { mode: "all" | "team" }) {
  const { can } = useSession();
  const today = new Date();
  const [from, setFrom] = useState(iso(new Date(today.getFullYear(), today.getMonth(), 1)));
  const [to, setTo] = useState(iso(today));
  const [role, setRole] = useState("");
  const [flagged, setFlagged] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<AttendanceItem | null>(null);
  const [correcting, setCorrecting] = useState(false);
  const list = useAttendanceList({ from, to, role, flagged, page });
  const data = list.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const canExport = can("attendance:export");
  const canCorrect = can("attendance:correct");

  const doExport = async (format: "xlsx" | "csv") => {
    try {
      await downloadExport({ from, to, format, role });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Ekspor gagal. Coba lagi.");
    }
  };
  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPage(1);
  };

  return (
    <>
      <PageHeader
        title={mode === "team" ? "Absensi team" : "Absensi"}
        action={
          <div className="flex gap-2">
            {canCorrect && <Button variant="secondary" onClick={() => setCorrecting(true)}>Koreksi absen</Button>}
            {canExport && (
              <>
                <Button variant="secondary" onClick={() => void doExport("csv")}>Ekspor CSV</Button>
                <Button onClick={() => void doExport("xlsx")}>Ekspor XLSX</Button>
              </>
            )}
          </div>
        }
      />
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-mist">Dari</span>
          <input type="date" aria-label="Dari tanggal" className={inputCls} value={from} onChange={(e) => reset(setFrom)(e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-mist">Sampai</span>
          <input type="date" aria-label="Sampai tanggal" className={inputCls} value={to} onChange={(e) => reset(setTo)(e.target.value)} />
        </label>
        <select aria-label="Filter role" className={inputCls} value={role} onChange={(e) => reset(setRole)(e.target.value)}>
          <option value="">Semua role</option>
          {["admin", "team_leader", "finance", "hes", "user"].map((v) => (
            <option key={v} value={v}>
              {ROLE_LABEL[v]}
            </option>
          ))}
        </select>
        <select aria-label="Filter tinjauan" className={inputCls} value={flagged} onChange={(e) => reset(setFlagged)(e.target.value)}>
          <option value="">Semua absen</option>
          <option value="true">Perlu ditinjau</option>
          <option value="false">Tanpa tanda</option>
        </select>
      </div>

      <div className="overflow-x-auto rounded-panel border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 border-b border-line bg-surface text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Karyawan</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Tanggal</th>
              <th className="px-4 py-3 font-medium">Jam</th>
              <th className="px-4 py-3 font-medium">Sumber</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {list.isError && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-danger">
                  Absensi tidak dapat dimuat.
                </td>
              </tr>
            )}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-mist">
                  Belum ada absensi pada rentang ini.
                </td>
              </tr>
            )}
            {data?.items.map((a) => (
              <tr key={a.id} className="h-11 cursor-pointer border-b border-line last:border-0 hover:bg-hover" onClick={() => setSelected(a)}>
                <td className="px-4 py-2">
                  <button type="button" className="font-medium text-lens hover:underline" onClick={() => setSelected(a)}>
                    {a.full_name}
                  </button>
                </td>
                <td className="px-4 py-2">{ROLE_LABEL[a.user_type ?? a.role]}</td>
                <td className="px-4 py-2">{formatDate(a.attendance_date)}</td>
                <td className="px-4 py-2">{a.is_manual ? "-" : formatDateTime(a.checked_in_at).slice(-9)}</td>
                <td className="px-4 py-2">{a.is_manual ? <Badge tone="info">Manual</Badge> : a.source === "WEB" ? "Web" : "Android"}</td>
                <td className="px-4 py-2">{a.risk_flags.length > 0 ? <Badge tone="warning">Perlu ditinjau</Badge> : <Badge tone="success">Normal</Badge>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.total > data.page_size && (
        <nav aria-label="Halaman" className="mt-4 flex items-center justify-between text-sm">
          <span className="text-mist">
            {data.total} absen · halaman {data.page} dari {lastPage}
          </span>
          <span className="flex gap-2">
            <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Sebelumnya
            </Button>
            <Button variant="secondary" disabled={page >= lastPage} onClick={() => setPage(page + 1)}>
              Berikutnya
            </Button>
          </span>
        </nav>
      )}

      {selected && <DetailPanel key={selected.id} item={selected} onClose={() => setSelected(null)} />}
      {correcting && <CorrectionDialog onClose={() => setCorrecting(false)} />}
    </>
  );
}
