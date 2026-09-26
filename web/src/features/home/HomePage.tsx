import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarClock, ClipboardCheck, FileCheck2, FileClock, FileWarning, MapPin } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useSession } from "@/app/session";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { formatDate } from "@/lib/format";
import { useWorkPlans } from "@/features/work-plans/api";

type AttendanceList = components["schemas"]["AttendanceListResponse"];
type ExpiringList = components["schemas"]["ExpiringDocumentList"];
type PendingList = components["schemas"]["PendingDocumentList"];

const WAITING = ["DRAFT", "PUBLISHED", "ACCEPTED", "APPEALED", "COMPLETION_REVIEW"];

function greeting(now = new Date()) {
  const hour = Number(new Intl.DateTimeFormat("id-ID", { hour: "numeric", hourCycle: "h23", timeZone: "Asia/Jakarta" }).format(now));
  if (hour < 11) return "Selamat pagi";
  if (hour < 15) return "Selamat siang";
  if (hour < 18) return "Selamat sore";
  return "Selamat malam";
}

function useAttendanceToReview(enabled: boolean) {
  return useQuery({
    queryKey: ["attendance", { status: "NEEDS_REVIEW", home: true }],
    enabled,
    queryFn: async () => (await api.get<AttendanceList>("/attendance", { params: { status: "NEEDS_REVIEW", page: 1, size: 1 } })).data.total,
  });
}

function Stat({ label, value, icon, to, loading }: { label: string; value: number | undefined; icon: ReactNode; to: string; loading: boolean }) {
  return (
    <Link to={to} className="group block rounded-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
      <Card className="h-full gap-3 py-5">
        <CardContent className="flex items-start justify-between gap-3 px-5">
          <div>
            <p className="text-body-sm text-mist">{label}</p>
            {loading ? <Skeleton className="mt-2 h-8 w-12" /> : <p className="mt-1 text-display text-ink">{value ?? 0}</p>}
          </div>
          <span className="grid size-10 place-items-center rounded-control bg-accent text-lens transition-transform duration-300 group-hover:scale-110" aria-hidden>
            {icon}
          </span>
        </CardContent>
      </Card>
    </Link>
  );
}

/** Beranda (R-12): sapaan, ringkasan angka, SK aktif, pintasan — semua dari endpoint yang sudah ada. */
/** M2: dokumen pribadi kedaluwarsa atau berakhir ≤ 30 hari (GET /documents/expiring, izin verify:documents). */
function useExpiringDocuments(enabled: boolean) {
  return useQuery({
    queryKey: ["documents", "expiring"],
    enabled,
    queryFn: async () =>
      (await api.get<ExpiringList>("/documents/expiring")).data.items.filter((d) => d.urgency !== "AMAN"),
  });
}

/** P2-5: antrean verifikasi HR — dokumen pribadi berstatus PENDING (GET /documents/pending). */
function usePendingDocuments(enabled: boolean) {
  return useQuery({
    queryKey: ["documents", "pending"],
    enabled,
    queryFn: async () => (await api.get<PendingList>("/documents/pending")).data.items,
  });
}

function PendingDocumentsCard({ items }: { items: PendingList["items"] }) {
  return (
    <Card className="gap-4">
      <CardHeader>
        <CardTitle className="text-heading">Dokumen menunggu verifikasi</CardTitle>
        <CardDescription>Terlama dulu. Unggahan Anda sendiri diperiksa petugas lain.</CardDescription>
      </CardHeader>
      <CardContent className="px-3 md:px-4">
        <ul className="divide-y divide-line">
          {items.slice(0, 8).map((d) => (
            <li key={d.id}>
              <Link
                to={`/directory/${d.employee_id}`}
                className="flex items-center gap-4 rounded-control px-3 py-3 transition-colors hover:bg-hover"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink">{d.full_name}</p>
                  <p className="mt-0.5 truncate text-body-sm text-mist">
                    {d.doc_type} · diunggah {formatDate(d.uploaded_at)}
                  </p>
                </div>
                {d.uploaded_by_me && <span className="shrink-0 text-xs text-mist">Unggahan Anda</span>}
                <ArrowRight size={18} aria-hidden className="shrink-0 text-mist" />
              </Link>
            </li>
          ))}
        </ul>
        {items.length > 8 && <p className="px-3 pt-2 text-body-sm text-mist">+{items.length - 8} dokumen lain.</p>}
      </CardContent>
    </Card>
  );
}

const URGENCY: Record<string, { label: string; tone: string }> = {
  KEDALUWARSA: { label: "Kedaluwarsa", tone: "bg-danger-bg text-danger" },
  KURANG_DARI_7_HARI: { label: "< 7 hari", tone: "bg-warning-bg text-warning" },
  KURANG_DARI_30_HARI: { label: "< 30 hari", tone: "bg-info-bg text-info" },
};

function ExpiringDocumentsCard({ items }: { items: ExpiringList["items"] }) {
  return (
    <Card className="gap-4">
      <CardHeader>
        <CardTitle className="text-heading">Dokumen mendekati kedaluwarsa</CardTitle>
        <CardDescription>Berakhir dalam 30 hari atau sudah lewat — minta karyawan memperpanjang.</CardDescription>
      </CardHeader>
      <CardContent className="px-3 md:px-4">
        <ul className="divide-y divide-line">
          {items.slice(0, 8).map((d) => (
            <li key={d.id}>
              <Link
                to={`/directory/${d.employee_id}`}
                className="flex items-center gap-4 rounded-control px-3 py-3 transition-colors hover:bg-hover"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink">{d.full_name}</p>
                  <p className="mt-0.5 truncate text-body-sm text-mist">
                    {d.doc_type} · berlaku s.d. {formatDate(d.expiry_date)}
                  </p>
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${URGENCY[d.urgency]?.tone ?? ""}`}>
                  {URGENCY[d.urgency]?.label ?? d.urgency}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        {items.length > 8 && <p className="px-3 pt-2 text-body-sm text-mist">+{items.length - 8} dokumen lain.</p>}
      </CardContent>
    </Card>
  );
}

export function HomePage() {
  const { me } = useSession();
  const perms = me?.permissions ?? [];
  const canReview = perms.includes("review:attendance") || perms.includes("review:unit_attendance");
  const plans = useWorkPlans({ status: "", archived: false });
  const toReview = useAttendanceToReview(canReview);
  const canVerifyDocs = perms.includes("verify:documents");
  const expiring = useExpiringDocuments(canVerifyDocs);
  const pending = usePendingDocuments(canVerifyDocs);

  const list = plans.data ?? [];
  const running = list.filter((p) => p.status === "IN_PROGRESS");
  const waiting = list.filter((p) => WAITING.includes(p.status));
  const active = [...running, ...waiting].slice(0, 6);
  const today = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" }).format(new Date());

  return (
    <div className="space-y-6 md:space-y-8">
      <header>
        <p className="text-body-sm text-mist">{today}</p>
        <h1 className="mt-1 text-title-lg text-ink md:text-display">
          {greeting()}
          <span className="text-mist">, {me?.email.split("@")[0]}</span>
        </h1>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Stat label="SK berjalan" value={running.length} loading={plans.isPending} icon={<CalendarClock size={20} />} to="/work-plans" />
        <Stat label="SK menunggu tindakan" value={waiting.length} loading={plans.isPending} icon={<FileClock size={20} />} to="/work-plans" />
        {canReview && (
          <Stat label="Absensi perlu diperiksa" value={toReview.data} loading={toReview.isPending} icon={<ClipboardCheck size={20} />} to="/attendance" />
        )}
        {canVerifyDocs && (
          <Stat label="Dokumen menunggu verifikasi" value={pending.data?.length} loading={pending.isPending} icon={<FileCheck2 size={20} />} to="/directory" />
        )}
        {canVerifyDocs && (
          <Stat label="Dokumen mendekati kedaluwarsa" value={expiring.data?.length} loading={expiring.isPending} icon={<FileWarning size={20} />} to="/directory" />
        )}
      </div>

      {canVerifyDocs && !!pending.data?.length && <PendingDocumentsCard items={pending.data} />}
      {canVerifyDocs && !!expiring.data?.length && <ExpiringDocumentsCard items={expiring.data} />}

      <Card className="gap-4">
        <CardHeader>
          <CardTitle className="text-heading">Pekerjaan aktif</CardTitle>
          <CardDescription>SK berjalan dan yang menunggu tindakan.</CardDescription>
        </CardHeader>
        <CardContent className="px-3 md:px-4">
          {plans.isPending && <Skeleton className="mx-3 h-14" />}
          {plans.isError && <p className="px-3 text-danger">Daftar SK tidak dapat dimuat.</p>}
          {plans.isSuccess && active.length === 0 && <p className="px-3 text-mist">Belum ada SK aktif.</p>}
          <ul className="divide-y divide-line">
            {active.map((p) => (
              <li key={p.id}>
                <Link
                  to={`/work-plans/${p.id}`}
                  className="group flex items-center gap-4 rounded-control px-3 py-3 transition-colors hover:bg-hover"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-ink">{p.title}</p>
                    <p className="mt-0.5 flex items-center gap-1.5 truncate text-body-sm text-mist">
                      <MapPin size={14} aria-hidden className="shrink-0" />
                      {p.location_text} · {formatDate(p.period_start)} – {formatDate(p.period_end)}
                    </p>
                  </div>
                  <StatusBadge status={p.status} />
                  <ArrowRight size={18} aria-hidden className="shrink-0 text-mist transition-transform duration-300 group-hover:translate-x-1" />
                </Link>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
