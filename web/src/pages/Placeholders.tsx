import { Link } from "react-router-dom";
import { PageHeader } from "@/components/ui/PageHeader";
import { useSession } from "@/app/session";

export function HomePage() {
  const { me } = useSession();
  return (
    <>
      <PageHeader title="Beranda" />
      <p className="text-mist">Selamat datang, {me?.full_name}.</p>
    </>
  );
}

export function ComingSoonPage({ title }: { title: string }) {
  return (
    <>
      <PageHeader title={title} />
      <p className="text-mist">Halaman ini dibangun pada fase berikutnya.</p>
    </>
  );
}

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



