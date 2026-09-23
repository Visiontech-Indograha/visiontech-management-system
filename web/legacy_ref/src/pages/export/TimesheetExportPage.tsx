import { useState } from "react";
import toast from "react-hot-toast";
import api from "../../lib/api";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

/**
 * Komponen halaman untuk melakukan export data operasional dan timesheet.
 * Halaman ini akan mengunduh file CSV berdasarkan rentang tanggal yang dipilih.
 */
const TimesheetExportPage = () => {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isExportingTimesheet, setIsExportingTimesheet] = useState(false);
  const [isExportingFinancial, setIsExportingFinancial] = useState(false);

  const downloadCsv = (data: BlobPart, filename: string) => {
    const blob = new Blob([data], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  /**
   * Mengunduh CSV Timesheet (Absensi & Cuti) dari backend.
   */
  const handleExportTimesheet = async () => {
    if (!startDate || !endDate) {
      toast.error("Harap isi tanggal mulai dan tanggal selesai.");
      return;
    }

    setIsExportingTimesheet(true);
    try {
      const response = await api.get("/api/v1/export/timesheet", {
        params: { start_date: startDate, end_date: endDate },
        responseType: "blob",
      });
      downloadCsv(response.data as BlobPart, `timesheet_${startDate}_to_${endDate}.csv`);
      toast.success("Timesheet berhasil diexport.");
    } catch {
      toast.error("Gagal melakukan export timesheet.");
    } finally {
      setIsExportingTimesheet(false);
    }
  };

  /**
   * Mengunduh CSV Rekapitulasi Keuangan (material + servis kendaraan) dari backend.
   */
  const handleExportFinancial = async () => {
    if (!startDate || !endDate) {
      toast.error("Harap isi tanggal mulai dan tanggal selesai.");
      return;
    }

    setIsExportingFinancial(true);
    try {
      const response = await api.get("/api/v1/export/financial-recap", {
        params: { start_date: startDate, end_date: endDate },
        responseType: "blob",
      });
      downloadCsv(response.data as BlobPart, `financial_recap_${startDate}_to_${endDate}.csv`);
      toast.success("Rekapitulasi keuangan berhasil diexport.");
    } catch {
      toast.error("Gagal melakukan export rekapitulasi keuangan.");
    } finally {
      setIsExportingFinancial(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Export Rekapitulasi & Timesheet</h1>
        <p className="mt-1 text-sm text-gray-500">
          Unduh laporan operasional lapangan dan keuangan dalam format CSV.
        </p>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200 p-6">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 mb-6">
          <Input label="Tanggal Mulai" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          <Input label="Tanggal Selesai" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          <Button onClick={handleExportTimesheet} disabled={isExportingTimesheet}>
            {isExportingTimesheet ? "Memproses..." : "Export Timesheet (Absensi & Cuti)"}
          </Button>
          <Button variant="secondary" onClick={handleExportFinancial} disabled={isExportingFinancial}>
            {isExportingFinancial ? "Memproses..." : "Export Rekapitulasi Keuangan"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default TimesheetExportPage;
