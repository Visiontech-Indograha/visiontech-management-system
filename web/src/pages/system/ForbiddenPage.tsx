import { SystemStatusTemplate } from "@/components/templates/system/SystemStatusTemplate";

/** Rute yang tidak diizinkan untuk peran pengguna. */
export function ForbiddenPage() {
  return <SystemStatusTemplate title="Akses ditolak" description="Anda tidak berwenang membuka halaman ini." />;
}
