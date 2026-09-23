import { useProgressReports } from "../../hooks/api/useFieldwork";
import { LoadingState, StatCard } from "../../components/ui/QueryState";

/**
 * Halaman Overview untuk Divisi Finance
 */
const FinancePage = () => {
  const { data: reports, isLoading } = useProgressReports();

  if (isLoading) {
    return <LoadingState label="Loading Finance Dashboard..." />;
  }

  // Aggregate BOM from reports
  let totalBOMItems = 0;
  reports?.forEach(r => {
    totalBOMItems += (r.bill_of_materials?.length || 0);
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Finance Overview</h1>
        <p className="mt-1 text-sm text-gray-500">Pemantauan rekapitulasi pengeluaran dan timesheet karyawan.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StatCard
          title="Pengeluaran BOM (Bill of Materials)"
          value={totalBOMItems}
          color="red"
          hint="Item BOM Tercatat dalam Laporan"
          linkTo="/finance/timesheet"
          linkLabel="Export Rekap Keuangan"
        />

        <StatCard
          title="Timesheet & Absensi"
          hint="Unduh rekapan waktu kerja (timesheet) untuk proses penggajian (payroll)."
          linkTo="/finance/timesheet"
          linkLabel="Export Timesheet"
        />
      </div>
    </div>
  );
}
export default FinancePage;
