import { ControlInput, ControlOption, ControlSelect } from "@/components/molecules/FormBlock";
const inputCls = "h-10 rounded-control border border-line bg-surface px-3 text-sm";

/** Cari nama/no. karyawan + saring status kerja. */
export function EmployeeListFilter({ q, onQChange, status, onStatusChange }: {
  q: string;
  onQChange: (q: string) => void;
  status: string;
  onStatusChange: (status: string) => void;
}) {
  return (
      <div className="mb-4 flex flex-wrap gap-3">
        <ControlInput
          aria-label="Cari nama atau no. karyawan"
          placeholder="Cari nama atau no. karyawan..."
          className={`${inputCls} w-full md:w-64`}
          value={q}
          onChange={(e) => onQChange(e.target.value)}
        />
        <ControlSelect aria-label="Filter status" className={inputCls} value={status} onChange={(e) => onStatusChange(e.target.value)}>
          <ControlOption value="active">Aktif</ControlOption>
          <ControlOption value="in_process">Proses keluar</ControlOption>
          <ControlOption value="offboarded">Selesai bekerja</ControlOption>
          <ControlOption value="archived">Diarsipkan</ControlOption>
          <ControlOption value="all">Semua</ControlOption>
        </ControlSelect>
      </div>
  );
}
