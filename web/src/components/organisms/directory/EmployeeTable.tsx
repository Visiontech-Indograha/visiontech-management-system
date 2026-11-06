import { useEffect, useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { formatDate } from "@/lib/format";
import type { EmployeeList } from "@/services/employeeService";
import { EmployeeStatusPill } from "./EmployeeStatusPill";
import { UserAvatar } from "@/components/organisms/UserAvatar";
import { ActionButton } from "@/components/molecules/ActionButton";
import { InlineLink } from "@/components/molecules/Links";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Direktori karyawan: kartu responsif di ponsel (< 768 px) dan tabel di layar lebar (≥ 768 px). */
export function EmployeeTable({ list }: { list: UseQueryResult<EmployeeList> }) {
  const [isCompact, setIsCompact] = useState(
    () => typeof window !== "undefined" && window.innerWidth > 0 && window.innerWidth < 768,
  );
  useEffect(() => {
    const onResize = () => setIsCompact(window.innerWidth > 0 && window.innerWidth < 768);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const data = list.data;
  const cols = 4;

  if (isCompact) {
    return (
      <div className="space-y-2.5">
        {list.isPending && (
          <div className="rounded-panel border border-line bg-surface p-4 shadow-card">
            <div className="h-4 w-1/2 animate-pulse rounded-tag bg-hover" />
          </div>
        )}
        {list.isError && (
          <div className="flex flex-col items-center gap-2 rounded-panel border border-line bg-surface p-6 text-center text-sm text-danger shadow-card">
            <TextBlock>Direktori tidak dapat dimuat.</TextBlock>
            <ActionButton variant="outline" size="sm" onClick={() => list.refetch()}>
              Coba lagi
            </ActionButton>
          </div>
        )}
        {data?.items.length === 0 && (
          <div className="rounded-panel border border-line bg-surface p-6 text-center text-sm text-mist shadow-card">
            <TextBlock>Tidak ada karyawan yang cocok.</TextBlock>
          </div>
        )}
        {data?.items.map((e) => (
          <InlineLink
            key={e.employee_id}
            to={`/directory/${e.employee_id}`}
            state={{ employee: e }}
            className="flex items-center justify-between gap-3 rounded-panel border border-line bg-surface p-3.5 shadow-card transition-colors hover:border-primary/40 hover:bg-hover"
          >
            <div className="flex min-w-0 items-center gap-3">
              <UserAvatar name={e.full_name} fileId={e.photo_file_id} size="sm" />
              <div className="min-w-0">
                <TextBlock className="truncate font-semibold text-lens">{e.full_name}</TextBlock>
                <TextBlock className="truncate text-xs text-mist">
                  {`${e.employee_no} · ${e.position_name ?? "-"}`}
                </TextBlock>
                <TextBlock className="text-[11px] text-mist">{`Bergabung ${formatDate(e.join_date)}`}</TextBlock>
              </div>
            </div>
            <EmployeeStatusPill status={e.offboarding_status} />
          </InlineLink>
        ))}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
      <TableBlock className="w-full text-left text-sm">
        <TableBlockHead className="sticky top-0 border-b border-line bg-surface text-mist">
          <TableBlockRow>
            <TableBlockHeaderCell className="px-4 py-3 font-medium">Nama</TableBlockHeaderCell>
            <TableBlockHeaderCell className="px-4 py-3 font-medium">Jabatan</TableBlockHeaderCell>
            <TableBlockHeaderCell className="px-4 py-3 font-medium">Bergabung</TableBlockHeaderCell>
            <TableBlockHeaderCell className="px-4 py-3 font-medium">Status</TableBlockHeaderCell>
          </TableBlockRow>
        </TableBlockHead>
        <TableBlockBody>
          {list.isPending && (
            <TableBlockRow aria-hidden>
              <TableBlockCell colSpan={cols} className="h-11 px-4">
                <div className="h-3 w-1/2 animate-pulse rounded-tag bg-hover" />
              </TableBlockCell>
            </TableBlockRow>
          )}
          {list.isError && (
            <TableBlockRow>
              <TableBlockCell colSpan={cols} className="px-4 py-6 text-center text-danger">
                Direktori tidak dapat dimuat.{" "}
                <ActionButton variant="outline" size="sm" onClick={() => list.refetch()}>
                  Coba lagi
                </ActionButton>
              </TableBlockCell>
            </TableBlockRow>
          )}
          {data?.items.length === 0 && (
            <TableBlockRow>
              <TableBlockCell colSpan={cols} className="px-4 py-6 text-center text-mist">
                Tidak ada karyawan yang cocok.
              </TableBlockCell>
            </TableBlockRow>
          )}
          {data?.items.map((e) => (
            <TableBlockRow key={e.employee_id} className="h-11 border-b border-line last:border-0 hover:bg-hover">
              <TableBlockCell className="px-4 py-2">
                <div className="flex items-center gap-3">
                  <UserAvatar name={e.full_name} fileId={e.photo_file_id} size="sm" />
                  <div>
                    <InlineLink to={`/directory/${e.employee_id}`} state={{ employee: e }} className="font-medium text-lens hover:underline">
                      {e.full_name}
                    </InlineLink>
                    <div className="text-xs text-mist">{e.employee_no}</div>
                  </div>
                </div>
              </TableBlockCell>
              <TableBlockCell className="px-4 py-2">{e.position_name ?? "-"}</TableBlockCell>
              <TableBlockCell className="px-4 py-2">{formatDate(e.join_date)}</TableBlockCell>
              <TableBlockCell className="px-4 py-2"><EmployeeStatusPill status={e.offboarding_status} /></TableBlockCell>
            </TableBlockRow>
          ))}
        </TableBlockBody>
      </TableBlock>
    </div>
  );
}
