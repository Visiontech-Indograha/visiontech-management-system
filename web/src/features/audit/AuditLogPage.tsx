import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/PageHeader";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const ACTIONS = [
  "auth.login_super_admin",
  "user.create",
  "user.update",
  "user.change_role",
  "user.reset_password",
  "user.deactivate",
  "user.activate",
  "user.bootstrap_super_admin",
];

interface AuditEvent {
  id: string;
  occurred_at: string;
  actor_label: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  detail: string | null;
  changes: Record<string, unknown> | null;
}

interface AuditEventListResponse {
  items: AuditEvent[];
  total: number;
  page: number;
  size: number;
}

export function AuditLogPage() {
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<string | null>(null);

  const logs = useQuery({
    queryKey: ["audit-events", action, page],
    queryFn: async () =>
      (await api.get<AuditEventListResponse>("/audit-events", { params: { page, size: 25, ...(action ? { action } : {}) } }))
        .data,
    placeholderData: keepPreviousData,
  });
  const data = logs.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <>
      <PageHeader title="Audit log" />
      <select
        aria-label="Filter aksi"
        className="mb-4 h-10 rounded-control border border-line bg-surface px-3 text-sm"
        value={action}
        onChange={(e) => {
          setAction(e.target.value);
          setPage(1);
        }}
      >
        <option value="">Semua aksi</option>
        {ACTIONS.map((a) => (
          <option key={a}>{a}</option>
        ))}
      </select>

      <div className="overflow-x-auto rounded-panel border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Waktu</th>
              <th className="px-4 py-3 font-medium">Aksi</th>
              <th className="px-4 py-3 font-medium">Entitas</th>
              <th className="px-4 py-3 font-medium">Aktor</th>
              <th className="px-4 py-3 text-right font-medium">Detail</th>
            </tr>
          </thead>
          <tbody>
            {logs.isError && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-danger">
                  Audit log tidak dapat dimuat.
                </td>
              </tr>
            )}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-mist">
                  Belum ada catatan.
                </td>
              </tr>
            )}
            {data?.items.map((l) => (
              <Fragment key={l.id}>
                <tr className="h-11 border-b border-line">
                  <td className="whitespace-nowrap px-4 py-2">{formatDateTime(l.occurred_at)}</td>
                  <td className="px-4 py-2 font-medium">{l.action}</td>
                  <td className="px-4 py-2 text-mist">
                    {l.entity_type} {l.entity_id?.slice(0, 8)}
                  </td>
                  <td className="px-4 py-2 text-mist">{l.actor_label}</td>
                  <td className="px-4 py-2 text-right">
                    <Button
                      variant="ghost"
                      className="h-8 px-2"
                      onClick={() => setOpen(open === l.id ? null : l.id)}
                      aria-expanded={open === l.id}
                    >
                      {open === l.id ? "Tutup" : "Lihat"}
                    </Button>
                  </td>
                </tr>
                {open === l.id && (
                  <tr className="border-b border-line bg-paper">
                    <td colSpan={5} className="px-4 py-3">
                      <pre className="overflow-x-auto text-xs">
                        {l.detail}
                        {l.changes && "\n" + JSON.stringify(l.changes, null, 2)}
                      </pre>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.total > data.size && (
        <nav aria-label="Halaman" className="mt-4 flex items-center justify-between text-sm">
          <span className="text-mist">
            {data.total} catatan · halaman {data.page} dari {lastPage}
          </span>
          <span className="flex gap-2">
            <Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Sebelumnya
            </Button>
            <Button variant="outline" disabled={page >= lastPage} onClick={() => setPage(page + 1)}>
              Berikutnya
            </Button>
          </span>
        </nav>
      )}
    </>
  );
}
