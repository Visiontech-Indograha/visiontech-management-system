const inputCls = "h-10 rounded-control border border-line bg-surface px-3 text-sm";

/** Cari nama/no. karyawan + saring status akun. */
export function EmployeeListFilter({ q, onQChange, status, onStatusChange }: {
  q: string;
  onQChange: (q: string) => void;
  status: string;
  onStatusChange: (status: string) => void;
}) {
  return (
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          aria-label="Cari nama atau no. karyawan"
          placeholder="Cari nama atau no. karyawan..."
          className={`${inputCls} w-full md:w-64`}
          value={q}
          onChange={(e) => onQChange(e.target.value)}
        />
        <select aria-label="Filter akun" className={inputCls} value={status} onChange={(e) => onStatusChange(e.target.value)}>
          <option value="active">Aktif</option>
          <option value="inactive">Nonaktif</option>
          <option value="all">Semua</option>
        </select>
      </div>
  );
}
