import { useWorkPlans } from "../../hooks/api/useFieldwork";
import { useVehicleBookings } from "../../hooks/api/useLogbooks";
import { LoadingState, StatCard } from "../../components/ui/QueryState";

/**
 * Halaman Overview untuk Operational Manager
 * Menampilkan ringkasan operasional dan persetujuan yang tertunda.
 */
const OMPage = () => {
  const { data: plans, isLoading: loadingPlans } = useWorkPlans();
  const { data: logbooks, isLoading: loadingLogs } = useVehicleBookings();

  if (loadingPlans || loadingLogs) {
    return <LoadingState label="Loading OM Dashboard..." />;
  }

  const activePlans = plans?.filter((p) => p.status === "ACTIVE") || [];
  const pendingLogs = logbooks?.filter((l) => l.approval_status === "PENDING") || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Operational Manager Overview</h1>
        <p className="mt-1 text-sm text-gray-500">Pemantauan manajerial tingkat tinggi dan persetujuan.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StatCard
          title="Work Plan"
          value={activePlans.length}
          color="indigo"
          hint="Penugasan Aktif (Seluruh Tim)"
          linkTo="/pm/work-plan"
          linkLabel="Pantau Work Plan"
        />

        <StatCard
          title="Peminjaman Kendaraan"
          value={pendingLogs.length}
          color="yellow"
          hint="Menunggu Persetujuan (Pending)"
          linkTo="/om/logbook"
          linkLabel="Kelola Logbook"
        />
      </div>
    </div>
  );
}
export default OMPage;
