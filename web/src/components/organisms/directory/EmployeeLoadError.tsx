import { Link } from "react-router-dom";

/** Galat memuat detail karyawan + tautan kembali ke Direktori. */
export function EmployeeLoadError({ message }: { message: string }) {
  return (
      <div className="mt-16 text-center">
        <p className="mb-3 text-danger">{message}</p>
        <Link to="/directory" className="font-semibold text-lens hover:underline">
          Kembali ke Direktori
        </Link>
      </div>
  );
}
