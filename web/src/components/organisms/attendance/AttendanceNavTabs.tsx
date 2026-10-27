import { InlineLink } from "@/components/molecules/Links";

export function AttendanceNavTabs({
  activeTab,
}: {
  activeTab: "attendance" | "leaves" | "recap";
}) {
  return (
    <div className="flex items-center gap-2 mb-4 border-b border-line pb-2 flex-wrap">
      <InlineLink
        to="/attendance"
        className={`px-3 py-1.5 rounded-control text-xs font-medium transition-colors ${
          activeTab === "attendance"
            ? "bg-primary text-white font-semibold"
            : "bg-hover text-foreground hover:bg-hover/80"
        }`}
      >
        Absensi Harian
      </InlineLink>
      <InlineLink
        to="/leaves"
        className={`px-3 py-1.5 rounded-control text-xs font-medium transition-colors ${
          activeTab === "leaves"
            ? "bg-primary text-white font-semibold"
            : "bg-hover text-foreground hover:bg-hover/80"
        }`}
      >
        Cuti & Izin Karyawan
      </InlineLink>
      <InlineLink
        to="/attendance-recap"
        className={`px-3 py-1.5 rounded-control text-xs font-medium transition-colors ${
          activeTab === "recap"
            ? "bg-primary text-white font-semibold"
            : "bg-hover text-foreground hover:bg-hover/80"
        }`}
      >
        Rekap Bulanan
      </InlineLink>
    </div>
  );
}
