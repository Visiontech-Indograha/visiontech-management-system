import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/atoms/Card";
import { formatDate } from "@/lib/format";
import type { PendingList } from "@/services/homeService";

/** P2-5: antrean verifikasi HR — dokumen pribadi berstatus PENDING (8 terlama). */
export function PendingDocumentsCard({ items }: { items: PendingList["items"] }) {
  return (
    <Card className="gap-4">
      <CardHeader>
        <CardTitle className="text-heading">Dokumen menunggu verifikasi</CardTitle>
        <CardDescription>Terlama dulu. Unggahan Anda sendiri diperiksa petugas lain.</CardDescription>
      </CardHeader>
      <CardContent className="px-3 md:px-4">
        <ul className="divide-y divide-line">
          {items.slice(0, 8).map((d) => (
            <li key={d.id}>
              <Link
                to={`/directory/${d.employee_id}`}
                className="flex items-center gap-4 rounded-control px-3 py-3 transition-colors hover:bg-hover"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink">{d.full_name}</p>
                  <p className="mt-0.5 truncate text-body-sm text-mist">
                    {d.doc_type} · diunggah {formatDate(d.uploaded_at)}
                  </p>
                </div>
                {d.uploaded_by_me && <span className="shrink-0 text-xs text-mist">Unggahan Anda</span>}
                <ArrowRight size={18} aria-hidden className="shrink-0 text-mist" />
              </Link>
            </li>
          ))}
        </ul>
        {items.length > 8 && <p className="px-3 pt-2 text-body-sm text-mist">+{items.length - 8} dokumen lain.</p>}
      </CardContent>
    </Card>
  );
}
