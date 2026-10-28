import type { UseQueryResult } from "@tanstack/react-query";
import { formatDate } from "@/lib/format";
import type { EmployeeList } from "@/services/employeeService";
import { EmployeeStatusPill } from "./EmployeeStatusPill";
import { ActionButton } from "@/components/molecules/ActionButton";
import { InlineLink } from "@/components/molecules/Links";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";

/** Tabel karyawan dengan keadaan memuat, galat (+ coba lagi), kosong, dan berhasil. */
export function EmployeeTable({ list }: { list: UseQueryResult<EmployeeList> }) {
  const data = list.data;
  const cols = 4;
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
                  <InlineLink to={`/directory/${e.employee_id}`} state={{ employee: e }} className="font-medium text-lens hover:underline">
                    {e.full_name}
                  </InlineLink>
                  <div className="text-xs text-mist">{e.employee_no}</div>
                </TableBlockCell>
                <TableBlockCell className="px-4 py-2">{e.position_name ?? e.division_name ?? e.office_name ?? "-"}{e.position_name && <div className="text-xs text-mist">{e.division_name ?? e.office_name}</div>}</TableBlockCell>
                <TableBlockCell className="px-4 py-2">{formatDate(e.join_date)}</TableBlockCell>
                <TableBlockCell className="px-4 py-2"><EmployeeStatusPill status={e.offboarding_status} /></TableBlockCell>
              </TableBlockRow>
            ))}
          </TableBlockBody>
        </TableBlock>
      </div>
  );
}
