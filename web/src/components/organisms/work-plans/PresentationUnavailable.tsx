import { Link } from "react-router-dom";

/** Pesan bila rencana kerja belum selesai (presentasi hanya untuk pekerjaan yang sudah selesai). */
export function PresentationUnavailable({ backTo }: { backTo: string }) {
  return (
    <>
        <h1 className="mb-2 text-xl font-semibold">Presentasi tidak tersedia</h1>
        <p className="mb-6 text-mist">Hanya pekerjaan yang sudah selesai yang dapat dipresentasikan.</p>
        <Link to={backTo} className="font-semibold text-lens hover:underline">
          Kembali
        </Link>
    </>
  );
}
