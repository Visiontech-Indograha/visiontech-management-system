import type { UseQueryResult } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { formatDateTime } from "@/lib/format";
import { ACTION_LABEL, AUDIT_ENTITIES, actorLabelAwam } from "@/lib/auditLabels";
import type { AuditEventList } from "@/services/auditService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";

/** Tabel audit log dengan baris detail yang bisa dibuka; keadaan memuat, galat (+ coba lagi), kosong, berhasil. */
export function AuditLogTable({ logs }: { logs: UseQueryResult<AuditEventList> }) {
  const [open, setOpen] = useState<string | null>(null);
  const data = logs.data;
  return (
      <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
        <TableBlock className="w-full text-left text-sm">
          <TableBlockHead className="border-b border-line text-mist">
            <TableBlockRow>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Waktu</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Aksi</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Entitas</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Aktor</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 text-right font-medium">Detail</TableBlockHeaderCell>
            </TableBlockRow>
          </TableBlockHead>
          <TableBlockBody>
            {logs.isPending && (
              <TableBlockRow aria-hidden>
                <TableBlockCell colSpan={5} className="px-4 py-3">
                  <LoadingBar className="h-4 w-1/2" />
                </TableBlockCell>
              </TableBlockRow>
            )}
            {logs.isError && (
              <TableBlockRow>
                <TableBlockCell colSpan={5} className="px-4 py-6 text-center text-danger">
                  Audit log tidak dapat dimuat.{" "}
                  <ActionButton variant="outline" size="sm" onClick={() => logs.refetch()}>
                    Coba lagi
                  </ActionButton>
                </TableBlockCell>
              </TableBlockRow>
            )}
            {data?.items.length === 0 && (
              <TableBlockRow>
                <TableBlockCell colSpan={5} className="px-4 py-6 text-center text-mist">
                  Belum ada catatan.
                </TableBlockCell>
              </TableBlockRow>
            )}
            {data?.items.map((l) => (
              <Fragment key={l.id}>
                <TableBlockRow className="h-11 border-b border-line">
                  <TableBlockCell className="whitespace-nowrap px-4 py-2">{formatDateTime(l.occurred_at)}</TableBlockCell>
                  <TableBlockCell className="px-4 py-2 font-medium">{ACTION_LABEL[l.action] ?? l.action}</TableBlockCell>
                  <TableBlockCell className="px-4 py-2 text-mist">
                    {AUDIT_ENTITIES[l.entity_type] ?? l.entity_type} {l.entity_id?.slice(0, 8)}
                  </TableBlockCell>
                  <TableBlockCell className="px-4 py-2 text-mist">{actorLabelAwam(l.actor_label)}</TableBlockCell>
                  <TableBlockCell className="px-4 py-2 text-right">
                    <ActionButton
                      variant="ghost"
                      className="h-8 px-2"
                      onClick={() => setOpen(open === l.id ? null : l.id)}
                      aria-expanded={open === l.id}
                    >
                      {open === l.id ? "Tutup" : "Lihat"}
                    </ActionButton>
                  </TableBlockCell>
                </TableBlockRow>
                {open === l.id && (
                  <TableBlockRow className="border-b border-line bg-paper">
                    <TableBlockCell colSpan={5} className="px-4 py-3">
                      <TextBlock as="pre" className="overflow-x-auto text-xs">
                        {l.detail}
                        {l.changes && "\n" + JSON.stringify(l.changes, null, 2)}
                      </TextBlock>
                    </TableBlockCell>
                  </TableBlockRow>
                )}
              </Fragment>
            ))}
          </TableBlockBody>
        </TableBlock>
      </div>
  );
}
