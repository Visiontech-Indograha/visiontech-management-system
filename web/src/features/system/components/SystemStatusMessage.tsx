import { Link } from "react-router-dom";

/** Pesan status sistem di tengah layar (akses ditolak, halaman tidak ditemukan) + tautan kembali ke Beranda. */
export function SystemStatusMessage({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mt-24 text-center">
      <h1 className="mb-2 text-2xl font-semibold">{title}</h1>
      {description && <p className="mb-4 text-mist">{description}</p>}
      <Link to="/" className="font-semibold text-lens hover:underline">
        Kembali ke Beranda
      </Link>
    </div>
  );
}
