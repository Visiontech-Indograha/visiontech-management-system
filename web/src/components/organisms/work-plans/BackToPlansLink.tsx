import { Link } from "react-router-dom";

/** Tautan kembali ke daftar rencana kerja. */
export function BackToPlansLink() {
  return (
      <p className="mt-6">
        <Link to="/work-plans" className="font-semibold text-lens hover:underline">
          Kembali ke daftar work plan
        </Link>
      </p>
  );
}
