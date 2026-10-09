import { SystemStatusMessage } from "@/components/organisms/system/SystemStatusMessage";

/** Rute yang tidak diizinkan untuk peran pengguna. */
export function ForbiddenPage() {
  return <SystemStatusMessage title="Akses ditolak" description="Anda tidak berwenang membuka halaman ini." />;
}
