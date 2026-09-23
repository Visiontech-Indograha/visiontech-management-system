import { useMemo, useState } from "react";
import {
  useDashboardSummary,
  useExpiringDocuments,
  useEmployeeStatus,
  useDailyReportRate,
  useFieldPerformance,
  useRecentActivity,
  useCalendarEvents,
} from "../../hooks/api/useDashboard";
import { Card } from "../../components/ui/Card";
import { Users, FileText, CheckCircle, Briefcase, Car, Wrench } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

const EVENT_COLOR: Record<string, string> = {
  WORK_PLAN: "bg-indigo-500",
  LEAVE: "bg-amber-500",
  DOCUMENT_EXPIRY: "bg-red-500",
};

const DashboardPage = () => {
  const { data, isLoading, error } = useDashboardSummary();
  const { user } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-gray-500">Loading dashboard data...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-red-500">Failed to load dashboard data.</p>
      </div>
    );
  }

  const role = user?.role;
  const isFinance = role === UserRole.FINANCE;
  const isPM = role === UserRole.PM;
  const isHR = role === UserRole.HR_HES;
  const isOM = role === UserRole.OM;
  const isAdmin = role === UserRole.ADMIN;
  const isManagement = isAdmin || isHR || isPM || isOM;

  const statCards = [];

  if (!isFinance && !isPM) {
    statCards.push({ title: "Total Karyawan", value: data.total_employees, icon: <Users className="h-6 w-6 text-blue-500" /> });
  }
  if (!isFinance && !isHR) {
    statCards.push({ title: "Proyek Aktif", value: data.active_projects, icon: <Briefcase className="h-6 w-6 text-green-500" /> });
  }
  if (!isFinance && !isPM) {
    statCards.push({ title: "Dokumen Expiring", value: data.expiring_documents_count, icon: <FileText className="h-6 w-6 text-yellow-500" /> });
  }
  if (!isHR) {
    statCards.push({ title: "Absensi Hari Ini", value: data.today_absences_count, icon: <CheckCircle className="h-6 w-6 text-indigo-500" /> });
  }
  if (isAdmin || isOM) {
    statCards.push({ title: "Kendaraan", value: data.vehicles_count, icon: <Car className="h-6 w-6 text-purple-500" /> });
    statCards.push({ title: "Alat", value: data.tools_count, icon: <Wrench className="h-6 w-6 text-orange-500" /> });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Ringkasan operasional Visiontech Management System
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat, idx) => (
          <Card key={idx}>
            <div className="flex items-center">
              <div className="flex-shrink-0">{stat.icon}</div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="truncate text-sm font-medium text-gray-500">{stat.title}</dt>
                  <dd>
                    <div className="text-2xl font-medium text-gray-900">{stat.value}</div>
                  </dd>
                </dl>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {isManagement && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {(isAdmin || isHR || isOM) && <EmployeeStatusWidget />}
          {(isAdmin || isHR || isOM) && <ExpiringDocumentsWidget />}
          {(isAdmin || isPM || isOM) && <DailyReportRateWidget />}
          {(isAdmin || isPM || isOM) && <FieldPerformanceWidget />}
          <CalendarWidget />
          <RecentActivityWidget />
        </div>
      )}
    </div>
  );
};

const WidgetCard = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <Card>
    <h2 className="mb-3 text-sm font-semibold text-gray-700">{title}</h2>
    {children}
  </Card>
);

const PIE_COLORS = ["#4f46e5", "#f59e0b", "#9ca3af"];

const EmployeeStatusWidget = () => {
  const { data, isLoading } = useEmployeeStatus();
  if (isLoading || !data) return <WidgetCard title="Status Karyawan"><p className="text-sm text-gray-400">Loading...</p></WidgetCard>;

  const chartData = [
    { name: "Tetap", value: data.tetap_count },
    { name: "Kontrak", value: data.kontrak_count },
    { name: "Belum diisi", value: data.unspecified_count },
  ].filter((d) => d.value > 0);

  return (
    <WidgetCard title="Status Karyawan (Tetap vs Kontrak)">
      {chartData.length === 0 ? (
        <p className="text-sm text-gray-400">Belum ada data.</p>
      ) : (
        <div className="flex items-center gap-4">
          <ResponsiveContainer width="60%" height={180}>
            <PieChart>
              <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
                {chartData.map((_, idx) => (
                  <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1 text-sm">
            <p>Tetap: <span className="font-semibold">{data.tetap_count}</span> ({data.tetap_percentage}%)</p>
            <p>Kontrak: <span className="font-semibold">{data.kontrak_count}</span> ({data.kontrak_percentage}%)</p>
            <p className="text-gray-500">Total aktif: {data.total}</p>
          </div>
        </div>
      )}
    </WidgetCard>
  );
};

const ExpiringDocumentsWidget = () => {
  const { data, isLoading } = useExpiringDocuments(90);
  if (isLoading) return <WidgetCard title="Dokumen Akan Kadaluarsa"><p className="text-sm text-gray-400">Loading...</p></WidgetCard>;

  const items = (data || []).slice(0, 8);
  return (
    <WidgetCard title="Dokumen Akan/Sudah Kadaluarsa (90 hari)">
      {items.length === 0 ? (
        <p className="text-sm text-gray-400">Tidak ada dokumen yang akan kadaluarsa.</p>
      ) : (
        <ul className="divide-y divide-gray-100 text-sm">
          {items.map((doc, idx) => (
            <li key={idx} className="flex items-center justify-between py-2">
              <div>
                <p className="font-medium text-gray-800">{doc.employee_name}</p>
                <p className="text-xs text-gray-500">{doc.label}</p>
              </div>
              <span className={`text-xs font-semibold ${doc.days_until_expiry < 0 ? "text-red-600" : doc.days_until_expiry <= 30 ? "text-orange-600" : "text-gray-500"}`}>
                {doc.days_until_expiry < 0 ? `Kadaluarsa ${Math.abs(doc.days_until_expiry)}h lalu` : `${doc.days_until_expiry} hari lagi`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </WidgetCard>
  );
};

const DailyReportRateWidget = () => {
  const { data, isLoading } = useDailyReportRate();
  if (isLoading || !data) return <WidgetCard title="Tingkat Laporan Harian"><p className="text-sm text-gray-400">Loading...</p></WidgetCard>;

  return (
    <WidgetCard title="Tingkat Laporan Harian Teknisi">
      <div className="space-y-2">
        <div className="flex items-end justify-between">
          <span className="text-3xl font-bold text-gray-900">{data.rate_percentage}%</span>
          <span className="text-sm text-gray-500">{data.reported_count}/{data.assigned_count} teknisi sudah lapor</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
          <div className="h-full bg-indigo-600" style={{ width: `${Math.min(data.rate_percentage, 100)}%` }} />
        </div>
        <p className="text-xs text-gray-400">Tanggal: {data.report_date}</p>
      </div>
    </WidgetCard>
  );
};

const FieldPerformanceWidget = () => {
  const { data, isLoading } = useFieldPerformance();
  if (isLoading || !data) return <WidgetCard title="Performa Lapangan"><p className="text-sm text-gray-400">Loading...</p></WidgetCard>;

  return (
    <WidgetCard title="Laporan Lapangan per Bulan (12 Bulan Terakhir)">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" fontSize={11} />
          <YAxis fontSize={11} allowDecimals={false} />
          <Tooltip />
          <Legend />
          <Bar dataKey="completed_reports" fill="#4f46e5" name="Laporan Masuk" />
        </BarChart>
      </ResponsiveContainer>
    </WidgetCard>
  );
};

const RecentActivityWidget = () => {
  const { data, isLoading } = useRecentActivity(15);
  if (isLoading) return <WidgetCard title="Aktivitas Terbaru"><p className="text-sm text-gray-400">Loading...</p></WidgetCard>;

  const items = data || [];
  return (
    <WidgetCard title="Aktivitas Terbaru">
      {items.length === 0 ? (
        <p className="text-sm text-gray-400">Belum ada aktivitas.</p>
      ) : (
        <ul className="max-h-72 space-y-2 overflow-y-auto text-sm">
          {items.map((item, idx) => (
            <li key={idx} className="border-b border-gray-100 pb-2 last:border-0">
              <p className="text-gray-800">{item.message}</p>
              <p className="text-xs text-gray-400">{new Date(item.timestamp).toLocaleString()}</p>
            </li>
          ))}
        </ul>
      )}
    </WidgetCard>
  );
};

const CalendarWidget = () => {
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });

  const { start, end, days } = useMemo(() => {
    const first = new Date(cursor.year, cursor.month, 1);
    const last = new Date(cursor.year, cursor.month + 1, 0);
    const fmt = (d: Date) => d.toISOString().split("T")[0];
    const dayList: Date[] = [];
    for (let d = 1; d <= last.getDate(); d++) {
      dayList.push(new Date(cursor.year, cursor.month, d));
    }
    return { start: fmt(first), end: fmt(last), days: dayList };
  }, [cursor]);

  const { data, isLoading } = useCalendarEvents(start, end);
  const eventsByDate = useMemo(() => {
    const map: Record<string, { type: string; title: string }[]> = {};
    for (const ev of data || []) {
      const key = ev.event_date;
      if (!map[key]) map[key] = [];
      map[key].push({ type: ev.type, title: ev.title });
    }
    return map;
  }, [data]);

  const monthLabel = new Date(cursor.year, cursor.month, 1).toLocaleDateString("id-ID", { month: "long", year: "numeric" });
  const firstWeekday = new Date(cursor.year, cursor.month, 1).getDay();

  return (
    <WidgetCard title="Calendar View">
      <div className="mb-2 flex items-center justify-between">
        <button onClick={() => setCursor((c) => (c.month === 0 ? { year: c.year - 1, month: 11 } : { year: c.year, month: c.month - 1 }))} className="rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100">‹</button>
        <span className="text-sm font-medium capitalize">{monthLabel}</span>
        <button onClick={() => setCursor((c) => (c.month === 11 ? { year: c.year + 1, month: 0 } : { year: c.year, month: c.month + 1 }))} className="rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100">›</button>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading...</p>
      ) : (
        <>
          <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-medium text-gray-400">
            {["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"].map((d) => <div key={d}>{d}</div>)}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {Array.from({ length: firstWeekday }).map((_, i) => <div key={`empty-${i}`} />)}
            {days.map((d) => {
              const key = d.toISOString().split("T")[0];
              const events = eventsByDate[key] || [];
              const isToday = key === new Date().toISOString().split("T")[0];
              return (
                <div key={key} className={`rounded p-1 text-center text-xs ${isToday ? "bg-indigo-50 font-semibold text-indigo-700" : "text-gray-700"}`}>
                  <div>{d.getDate()}</div>
                  {events.length > 0 && (
                    <div className="mt-0.5 flex justify-center gap-0.5">
                      {events.slice(0, 3).map((ev, idx) => (
                        <span key={idx} className={`h-1.5 w-1.5 rounded-full ${EVENT_COLOR[ev.type] || "bg-gray-400"}`} title={ev.title} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <ul className="mt-3 max-h-40 space-y-1 overflow-y-auto text-xs">
            {Object.entries(eventsByDate).sort(([a], [b]) => a.localeCompare(b)).flatMap(([date, events]) =>
              events.map((ev, idx) => (
                <li key={`${date}-${idx}`} className="flex items-center gap-2">
                  <span className={`h-1.5 w-1.5 rounded-full ${EVENT_COLOR[ev.type] || "bg-gray-400"}`} />
                  <span className="text-gray-400">{date}</span>
                  <span className="text-gray-700">{ev.title}</span>
                </li>
              ))
            )}
            {Object.keys(eventsByDate).length === 0 && <li className="text-gray-400">Tidak ada event bulan ini.</li>}
          </ul>
        </>
      )}
    </WidgetCard>
  );
};

export default DashboardPage;
