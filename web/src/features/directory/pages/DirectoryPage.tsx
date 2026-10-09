import { useState } from "react";
import { useSession } from "@/app/session";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { PAGE_SIZE, useEmployees } from "../employeeService";
import { EmployeeCreateButton } from "../components/EmployeeCreateButton";
import { CreateEmployeeDialog } from "../components/EmployeeLifecycleDialogs";
import { EmployeeListFilter } from "../components/EmployeeListFilter";
import { EmployeePagination } from "../components/EmployeePagination";
import { EmployeeTable } from "../components/EmployeeTable";

/** Direktori karyawan: cari, saring status, halaman per 20 (GET /employees). */
export function DirectoryPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("active");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const canManage = !!useSession().me?.permissions.includes("manage:users");
  const search = useDebouncedValue(q, 300);
  const list = useEmployees({ q: search, status, page });
  const data = list.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPage(1);
  };

  return (
    <PageTemplate title="Direktori" action={canManage && <EmployeeCreateButton onCreate={() => setCreating(true)} />}>
      {creating && <CreateEmployeeDialog onClose={() => setCreating(false)} />}
      <EmployeeListFilter q={q} onQChange={reset(setQ)} status={status} onStatusChange={reset(setStatus)} />
      <EmployeeTable list={list} />
      {data && data.total > PAGE_SIZE && (
        <EmployeePagination total={data.total} page={page} shownPage={data.page} lastPage={lastPage} onPageChange={setPage} />
      )}
    </PageTemplate>
  );
}
