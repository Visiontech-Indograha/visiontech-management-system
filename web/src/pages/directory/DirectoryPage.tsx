import { useState } from "react";
import { useSession } from "@/stores/sessionStore";
import { DirectoryTemplate } from "@/components/templates/directory/DirectoryTemplate";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useEmployees } from "@/services/employeeService";

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
    <DirectoryTemplate
      list={list}
      canManage={canManage}
      creating={creating}
      onCreate={() => setCreating(true)}
      onCloseCreate={() => setCreating(false)}
      q={q}
      onQChange={reset(setQ)}
      status={status}
      onStatusChange={reset(setStatus)}
      page={page}
      lastPage={lastPage}
      onPageChange={setPage}
    />
  );
}
