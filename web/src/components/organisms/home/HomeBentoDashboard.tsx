/**
 * web/src/components/organisms/home/HomeBentoDashboard.tsx
 * Bento UI Dashboard Eksekutif & Operasional VMS V2.
 * Mengintegrasikan Ringkasan KPI, Peta Sebaran Operasional (Leaflet),
 * Pemantauan Jadwal Berjalan, dan Pintasan Cepat Operasional.
 */

import React, { useState } from "react";
import { MapContainer, Marker, Popup, Circle } from "react-leaflet";
import { MapTiles } from "@/components/organisms/map/MapTiles";
import { useSites } from "@/services/siteService";
import type { WorkPlan } from "@/services/workPlanService";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { InlineLink } from "@/components/molecules/Links";
import { Button } from "@/components/atoms/Button";
import {
  Activity,
  ArrowUpRight,
  Calendar,
  CheckCircle2,
  Clock,
  Compass,
  FileSpreadsheet,
  HardHat,
  MapPin,
  ShieldCheck,
  Truck,
  Users,
} from "lucide-react";

export interface HomeBentoDashboardProps {
  plans: WorkPlan[];
  runningCount: number;
  waitingCount: number;
  reviewAttendanceCount?: number;
  canCreatePlan?: boolean;
}

export const HomeBentoDashboard: React.FC<HomeBentoDashboardProps> = ({
  plans,
  runningCount,
  waitingCount,
  reviewAttendanceCount = 0,
  canCreatePlan = false,
}) => {
  const sitesQuery = useSites();
  const sites = sitesQuery.data ?? [];

  // Default coordinate center (Jakarta / Jabodetabek or first site)
  const defaultCenter: [number, number] =
    sites.length > 0 && sites[0].location?.lat && sites[0].location?.lng
      ? [sites[0].location.lat, sites[0].location.lng]
      : [-6.2088, 106.8456];

  const [activeTab, setActiveTab] = useState<"all" | "in_progress">("in_progress");

  const filteredPlans = activeTab === "all"
    ? plans.slice(0, 5)
    : plans.filter((p) => p.status === "IN_PROGRESS").slice(0, 5);

  return (
    <div className="space-y-6">
      {/* 1. Bento Top Row: KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Proyek Aktif */}
        <div className="p-4 rounded-xl border border-line bg-surface shadow-card flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-mist uppercase tracking-wider">Proyek Berjalan</p>
            <h3 className="text-2xl font-bold text-ink mt-1">{runningCount}</h3>
            <span className="inline-flex items-center text-[11px] text-emerald-600 mt-1 font-medium">
              <Activity className="w-3 h-3 mr-1" /> Lapangan Aktif
            </span>
          </div>
          <div className="p-3 rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
            <HardHat className="w-6 h-6" />
          </div>
        </div>

        {/* Antrean Verifikasi */}
        <div className="p-4 rounded-xl border border-line bg-surface shadow-card flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-mist uppercase tracking-wider">Menunggu Tindakan</p>
            <h3 className="text-2xl font-bold text-ink mt-1">{waitingCount}</h3>
            <span className="inline-flex items-center text-[11px] text-amber-600 mt-1 font-medium">
              <Clock className="w-3 h-3 mr-1" /> Butuh Approval
            </span>
          </div>
          <div className="p-3 rounded-lg bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        {/* Review Absensi */}
        <div className="p-4 rounded-xl border border-line bg-surface shadow-card flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-mist uppercase tracking-wider">Review Absensi</p>
            <h3 className="text-2xl font-bold text-ink mt-1">{reviewAttendanceCount}</h3>
            <span className="inline-flex items-center text-[11px] text-sky-600 mt-1 font-medium">
              <ShieldCheck className="w-3 h-3 mr-1" /> GPS / Luar Radius
            </span>
          </div>
          <div className="p-3 rounded-lg bg-sky-50 text-sky-600 dark:bg-sky-950/40 dark:text-sky-400">
            <Users className="w-6 h-6" />
          </div>
        </div>

        {/* Titik Site Terdaftar */}
        <div className="p-4 rounded-xl border border-line bg-surface shadow-card flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-mist uppercase tracking-wider">Site Operasional</p>
            <h3 className="text-2xl font-bold text-ink mt-1">{sites.length}</h3>
            <span className="inline-flex items-center text-[11px] text-indigo-600 mt-1 font-medium">
              <Compass className="w-3 h-3 mr-1" /> Terpetakan GPS
            </span>
          </div>
          <div className="p-3 rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400">
            <MapPin className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* 2. Bento Middle Grid: Interactive Map + Schedule Tracker */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Peta Sebaran Operasional (7 cols) */}
        <div className="lg:col-span-7 rounded-xl border border-line bg-surface shadow-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-ink flex items-center gap-2">
                <MapPin className="w-4 h-4 text-sky-600" />
                Peta Sebaran Operasional Lapangan
              </h3>
              <p className="text-xs text-mist">
                Titik site proyek dan kantor operasional aktif terverifikasi radius GPS.
              </p>
            </div>
            <InlineLink
              to="/sites"
              className="text-xs font-medium text-sky-600 hover:text-sky-700 flex items-center gap-1"
            >
              Kelola Site <ArrowUpRight className="w-3.5 h-3.5" />
            </InlineLink>
          </div>

          <div className="relative isolate h-72 sm:h-80 w-full overflow-hidden rounded-lg border border-line">
            <MapContainer
              center={defaultCenter}
              zoom={11}
              scrollWheelZoom={false}
              className="h-full w-full"
            >
              <MapTiles />
              {sites.map((s) => {
                if (!s.location?.lat || !s.location?.lng) return null;
                const pos: [number, number] = [s.location.lat, s.location.lng];
                return (
                  <React.Fragment key={s.id}>
                    <Marker position={pos}>
                      <Popup>
                        <div className="text-xs space-y-1">
                          <p className="font-semibold text-ink">{s.name}</p>
                          <p className="text-mist">{s.address || "Lokasi operasional"}</p>
                          <p className="text-[10px] text-sky-600">
                            Radius: {s.radius_m ? `${s.radius_m}m` : "Standar"}
                          </p>
                        </div>
                      </Popup>
                    </Marker>
                    {s.radius_m && (
                      <Circle
                        center={pos}
                        radius={s.radius_m}
                        pathOptions={{
                          color: "#0284c7",
                          fillColor: "#0284c7",
                          fillOpacity: 0.15,
                        }}
                      />
                    )}
                  </React.Fragment>
                );
              })}
            </MapContainer>
          </div>

          <div className="mt-3 flex items-center justify-between text-xs text-mist">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-500 inline-block" />
              Titik Site Proyek Klien
            </span>
            <span>Total {sites.length} Titik Lokasi Terpantau</span>
          </div>
        </div>

        {/* Monitoring Jadwal Berjalan (5 cols) */}
        <div className="lg:col-span-5 rounded-xl border border-line bg-surface shadow-card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-base font-semibold text-ink flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-emerald-600" />
                  Monitoring Jadwal Berjalan
                </h3>
                <p className="text-xs text-mist">Progres rencana kerja dan status lapangan terkini.</p>
              </div>
              <InlineLink
                to="/work-plans"
                className="text-xs font-medium text-sky-600 hover:text-sky-700 flex items-center gap-1"
              >
                Semua <ArrowUpRight className="w-3.5 h-3.5" />
              </InlineLink>
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center gap-2 mb-3">
              <button
                type="button"
                onClick={() => setActiveTab("in_progress")}
                className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                  activeTab === "in_progress"
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                    : "bg-surface-muted text-mist hover:text-ink"
                }`}
              >
                Berjalan ({plans.filter((p) => p.status === "IN_PROGRESS").length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("all")}
                className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                  activeTab === "all"
                    ? "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
                    : "bg-surface-muted text-mist hover:text-ink"
                }`}
              >
                Semua Terakhir ({plans.length})
              </button>
            </div>

            {/* Plans List */}
            <div className="space-y-2.5 max-h-[290px] overflow-y-auto pr-1">
              {filteredPlans.length === 0 ? (
                <div className="py-8 text-center text-xs text-mist">
                  Tidak ada rencana kerja dalam kategori ini.
                </div>
              ) : (
                filteredPlans.map((p) => (
                  <InlineLink
                    key={p.id}
                    to={`/work-plans/${p.id}`}
                    className="block p-3 rounded-lg border border-line bg-surface-muted hover:border-sky-400 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-ink group-hover:text-sky-600 truncate">
                          {p.title || p.number || "Rencana Kerja"}
                        </p>
                        <p className="text-[11px] text-mist truncate">
                          {p.location_text || "Lokasi belum ditentukan"}
                        </p>
                      </div>
                      <StatusBadge status={p.status} />
                    </div>
                    <div className="mt-2 flex items-center justify-between text-[10px] text-mist">
                      <span>{p.period_start} s.d. {p.period_end}</span>
                      <span className="font-medium text-ink">Revisi: {p.revision}</span>
                    </div>
                  </InlineLink>
                ))
              )}
            </div>
          </div>

          {canCreatePlan && (
            <div className="mt-4 pt-3 border-t border-line">
              <Button asChild size="sm" className="w-full text-xs">
                <InlineLink to="/work-plans/new">
                  + Buat Rencana Kerja Baru
                </InlineLink>
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* 3. Bento Bottom Row: Quick Operational Shortcuts */}
      <div className="rounded-xl border border-line bg-surface shadow-card p-4">
        <p className="text-xs font-semibold text-mist uppercase tracking-wider mb-3">
          Pintasan Cepat Operasional
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <InlineLink
            to="/work-plans"
            className="flex items-center gap-3 p-3 rounded-lg border border-line bg-surface-muted hover:bg-sky-50 dark:hover:bg-sky-950/20 hover:border-sky-300 transition-colors"
          >
            <div className="p-2 rounded bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300">
              <FileSpreadsheet className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-ink">Rencana Kerja</p>
              <p className="text-[10px] text-mist">SPK & Tugas Harian</p>
            </div>
          </InlineLink>

          <InlineLink
            to="/attendance"
            className="flex items-center gap-3 p-3 rounded-lg border border-line bg-surface-muted hover:bg-emerald-50 dark:hover:bg-emerald-950/20 hover:border-emerald-300 transition-colors"
          >
            <div className="p-2 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-ink">Absensi GPS</p>
              <p className="text-[10px] text-mist">Radius & Uang Makan</p>
            </div>
          </InlineLink>

          <InlineLink
            to="/assets"
            className="flex items-center gap-3 p-3 rounded-lg border border-line bg-surface-muted hover:bg-amber-50 dark:hover:bg-amber-950/20 hover:border-amber-300 transition-colors"
          >
            <div className="p-2 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
              <Truck className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-ink">Armada & Alat</p>
              <p className="text-[10px] text-mist">Inspeksi & Alokasi</p>
            </div>
          </InlineLink>

          <InlineLink
            to="/offboarding"
            className="flex items-center gap-3 p-3 rounded-lg border border-line bg-surface-muted hover:bg-rose-50 dark:hover:bg-rose-950/20 hover:border-rose-300 transition-colors"
          >
            <div className="p-2 rounded bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-ink">Offboarding</p>
              <p className="text-[10px] text-mist">Clearance & Serah Terima</p>
            </div>
          </InlineLink>
        </div>
      </div>
    </div>
  );
};
