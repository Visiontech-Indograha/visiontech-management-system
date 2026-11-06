import { isRouteErrorResponse, useRouteError } from "react-router-dom";
import { SystemStatusTemplate } from "@/components/templates/system/SystemStatusTemplate";

/** Dipakai sebagai errorElement router: galat tak terduga tampil dalam bahasa sehari-hari. */
export function RouteErrorPage() {
  const error = useRouteError();
  if (import.meta.env.DEV) console.error(error);

  if (isRouteErrorResponse(error) && error.status === 404) {
    return <SystemStatusTemplate title="Halaman tidak ditemukan" description="Alamat yang Anda buka tidak tersedia. Kembali ke Beranda lalu pilih menu lain." />;
  }
  return (
    <SystemStatusTemplate
      title="Maaf, halaman ini gagal dibuka"
      description="Coba muat ulang halaman ini. Jika masih gagal, kembali ke Beranda lalu coba lagi."
    />
  );
}
