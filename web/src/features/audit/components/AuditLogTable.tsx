import type { UseQueryResult } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { Button } from "@/components/atoms/Button";
import { Skeleton } from "@/components/atoms/Skeleton";
import { formatDateTime } from "@/lib/format";
import { ACTION_LABEL, AUDIT_ENTITIES } from "../auditLabels";
import type { AuditEventList } from "../auditService";

/** Tabel audit log dengan baris detail yang bisa dibuka; keadaan memuat, galat (+ coba lagi), kosong, berhasil. */
export function AuditLogTable({ logs }: { logs: UseQueryResult<AuditEventList> }) {
  const [open, setOpen] = useState<string | null>(null);
  const data = logs.data;
  return (
      <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
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
            {logs.isPending && (
              <tr aria-hidden>
                <td colSpan={5} className="px-4 py-3">
                  <Skeleton className="h-4 w-1/2" />
                </td>
              </tr>
            )}
            {logs.isError && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-danger">
                  Audit log tidak dapat dimuat.{" "}
                  <Button variant="outline" size="sm" onClick={() => logs.refetch()}>
                    Coba lagi
                  </Button>
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
                  <td className="px-4 py-2 font-medium">{ACTION_LABEL[l.action] ?? l.action}</td>
                  <td className="px-4 py-2 text-mist">
                    {AUDIT_ENTITIES[l.entity_type] ?? l.entity_type} {l.entity_id?.slice(0, 8)}
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
  );
}
