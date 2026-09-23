import { Link } from "react-router-dom";
import { useSession } from "@/app/session";
import { PageHeader } from "@/components/ui/PageHeader";
import { DocumentsPanel } from "./DocumentsPanel";
import { CompletenessBadge } from "./badges";
import { useMyCompleteness } from "./api";

/** "Berkas saya": status kelengkapan dan daftar berkas milik sendiri (WTL, Driver). */
export function MyDocumentsPage() {
  const { me } = useSession();
  const completeness = useMyCompleteness(me?.id);
  const c = completeness.data;
  return (
    <>
      <PageHeader title="Berkas saya" action={c && <CompletenessBadge status={c.status} missing={c.missing.length} />} />
      {c && c.missing.length > 0 && (
        <p role="status" className="mb-4 rounded-control bg-warning-soft px-3 py-2 text-sm text-warning">
          {c.missing.length} berkas belum lengkap: {c.missing.map((m) => m.name).join(", ")}. Serahkan ke HES untuk diunggah.
        </p>
      )}
      {me && <DocumentsPanel userId={me.id} canManage={false} />}
    </>
  );
}

/** Banner non-blokir untuk pemilik berkas yang belum lengkap (FR-DOC-07). */
export function IncompleteDocumentsBanner() {
  const { me } = useSession();
  const info = me?.documents_incomplete;
  if (!info || info.count === 0) return null;
  return (
    <div role="status" className="border-b border-line bg-warning-soft px-4 py-2 text-sm text-warning">
      {info.count} berkas belum lengkap: {info.missing.join(", ")}.{" "}
      {me?.permissions.includes("employee_document:read_own") && !me.permissions.includes("employee:read") && (
        <Link to="/my-documents" className="font-semibold underline">
          Lihat berkas saya
        </Link>
      )}
    </div>
  );
}
