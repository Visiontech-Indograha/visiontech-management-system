import { useDashboardSummary } from "../../hooks/api/useDashboard";
import { LoadingState, StatCard } from "../../components/ui/QueryState";

/**
 * Halaman Overview untuk Divisi HES (Health, Environment, Safety) dan HR
 */
const HESPage = () => {
  const { data, isLoading } = useDashboardSummary();

  if (isLoading) {
    return <LoadingState label="Loading HES Dashboard..." />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">HES & HR Overview</h1>
        <p className="mt-1 text-sm text-gray-500">Pemantauan Karyawan, Dokumen Perizinan (K3), dan Portofolio.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="SDM & Karyawan"
          value={data?.total_employees || 0}
          color="blue"
          hint="Total Karyawan Aktif"
          linkTo="/hr/employees"
          linkLabel="Kelola Data Karyawan"
        />

        <StatCard
          title="Cuti & Kehadiran"
          value={data?.today_absences_count || 0}
          color="green"
          hint="Absensi Hari Ini"
          linkTo="/hr/leave"
          linkLabel="Persetujuan Cuti"
        />

        <StatCard
          title="Lisensi & Dokumen (HES)"
          value={data?.expiring_documents_count || 0}
          color="red"
          hint="Dokumen Expired / Mendekati Expired"
          footer={<span className="text-sm text-gray-400 italic">Menu Sertifikasi (WIP)</span>}
        />
      </div>
    </div>
  );
}
export default HESPage;
