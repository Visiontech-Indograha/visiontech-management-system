import { useSession } from "@/app/session";
import { PageHeader } from "@/components/ui/PageHeader";
import { DocumentsPanel } from "./DocumentsPanel";

/** "Berkas saya": daftar berkas milik sendiri (WTL, Driver). */
export function MyDocumentsPage() {
  const { me } = useSession();
  return (
    <>
      <PageHeader title="Berkas saya" />
      {me && <DocumentsPanel userId={me.id} canManage={false} />}
    </>
  );
}

/** Banner non-blokir dihapus karena kelengkapan dihapus dari UI. */
export function IncompleteDocumentsBanner() {
  return null;
}
