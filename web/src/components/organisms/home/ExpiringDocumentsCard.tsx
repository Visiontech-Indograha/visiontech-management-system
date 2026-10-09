import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/atoms/Card";
import { formatDate } from "@/lib/format";
import type { ExpiringList } from "@/services/homeService";

const URGENCY: Record<string, { label: string; tone: string }> = {
  KEDALUWARSA: { label: "Kedaluwarsa", tone: "bg-danger-bg text-danger" },
  KURANG_DARI_7_HARI: { label: "< 7 hari", tone: "bg-warning-bg text-warning" },
  KURANG_DARI_30_HARI: { label: "< 30 hari", tone: "bg-info-bg text-info" },
};

/** M2: dokumen pribadi kedaluwarsa atau berakhir ≤ 30 hari (8 teratas). */
export function ExpiringDocumentsCard({ items }: { items: ExpiringList["items"] }) {
  return (
    <Card className="gap-4">
      <CardHeader>
        <CardTitle className="text-heading">Dokumen mendekati kedaluwarsa</CardTitle>
        <CardDescription>Berakhir dalam 30 hari atau sudah lewat — minta karyawan memperpanjang.</CardDescription>
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
                    {d.doc_type} · berlaku s.d. {formatDate(d.expiry_date)}
                  </p>
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${URGENCY[d.urgency]?.tone ?? ""}`}>
                  {URGENCY[d.urgency]?.label ?? d.urgency}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        {items.length > 8 && <p className="px-3 pt-2 text-body-sm text-mist">+{items.length - 8} dokumen lain.</p>}
      </CardContent>
    </Card>
  );
}
