import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="mt-24 text-center">
      <h1 className="mb-2 text-2xl font-semibold">Halaman tidak ditemukan</h1>
      <Link to="/" className="font-semibold text-lens hover:underline">
        Kembali ke Beranda
      </Link>
    </div>
  );
}
