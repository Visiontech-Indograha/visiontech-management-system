import type { UseQueryResult } from "@tanstack/react-query";
import { ListPagination } from "@/components/organisms/ListPagination";
import { EmployeeCreateButton } from "@/components/organisms/directory/EmployeeCreateButton";
import { EmployeeCreateDialog } from "@/components/organisms/directory/EmployeeCreateDialog";
import { EmployeeListFilter } from "@/components/organisms/directory/EmployeeListFilter";
import { EmployeeTable } from "@/components/organisms/directory/EmployeeTable";
import { PAGE_SIZE, type EmployeeList } from "@/services/employeeService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka Direktori: cari & saring, tabel karyawan, halaman, dialog tambah karyawan. */
export function DirectoryTemplate({ list, canManage, creating, onCreate, onCloseCreate, q, onQChange, status, onStatusChange, page, lastPage, onPageChange }: {
  list: UseQueryResult<EmployeeList>;
  canManage: boolean;
  creating: boolean;
  onCreate: () => void;
  onCloseCreate: () => void;
  q: string;
  onQChange: (q: string) => void;
  status: string;
  onStatusChange: (status: string) => void;
  page: number;
  lastPage: number;
  onPageChange: (page: number) => void;
}) {
  const data = list.data;
  return (
    <PageTemplate title="Direktori" action={canManage && <EmployeeCreateButton onCreate={onCreate} />}>
      {creating && <EmployeeCreateDialog onClose={onCloseCreate} />}
      <EmployeeListFilter q={q} onQChange={onQChange} status={status} onStatusChange={onStatusChange} />
      <EmployeeTable list={list} />
      {data && data.total > PAGE_SIZE && (
        <ListPagination total={data.total} noun="karyawan" page={page} shownPage={data.page} lastPage={lastPage} onPageChange={onPageChange} />
      )}
    </PageTemplate>
  );
}
