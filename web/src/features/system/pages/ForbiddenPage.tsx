import { Link } from "react-router-dom";

export function ForbiddenPage() {
  return (
    <div className="mt-24 text-center">
      <h1 className="mb-2 text-2xl font-semibold">Akses ditolak</h1>
      <p className="mb-4 text-mist">Anda tidak berwenang membuka halaman ini.</p>
      <Link to="/" className="font-semibold text-lens hover:underline">
        Kembali ke Beranda
      </Link>
    </div>
  );
}
