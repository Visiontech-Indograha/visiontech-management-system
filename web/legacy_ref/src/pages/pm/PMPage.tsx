import { useWorkPlans, useProgressReports } from "../../hooks/api/useFieldwork";
import { LoadingState, StatCard } from "../../components/ui/QueryState";

/**
 * Halaman Overview untuk Project Manager
 * Menampilkan ringkasan operasional dan tautan cepat ke modul PM.
 */
const PMPage = () => {
  const { data: plans, isLoading: loadingPlans } = useWorkPlans();
  const { data: reports, isLoading: loadingReports } = useProgressReports();

  if (loadingPlans || loadingReports) {
    return <LoadingState label="Loading PM Dashboard..." />;
  }

  const activePlans = plans?.filter((p) => p.status === "ACTIVE") || [];
  const recentReports = reports?.slice(0, 5) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Project Manager Overview</h1>
        <p className="mt-1 text-sm text-gray-500">Ringkasan penugasan (Work Plan) dan laporan dari lapangan.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StatCard
          title="Status Work Plan"
          value={activePlans.length}
          color="blue"
          hint="Penugasan Aktif"
          linkTo="/pm/work-plan"
          linkLabel="Kelola Work Plan"
        />

        <StatCard
          title="Laporan Progres Terbaru"
          linkTo="/pm/progress"
          linkLabel="Lihat Semua Laporan"
          footer={
            recentReports.length === 0 ? (
              <p className="text-sm text-gray-500 mb-4">Belum ada laporan.</p>
            ) : (
              <ul className="space-y-3 mb-4">
                {recentReports.map((r) => (
                  <li key={r.id} className="text-sm">
                    <span className="font-medium">{new Date(r.created_at).toLocaleDateString()}</span> - {r.report_type}
                  </li>
                ))}
              </ul>
            )
          }
        />
      </div>
    </div>
  );
}
export default PMPage;
