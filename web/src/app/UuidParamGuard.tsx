import type { ReactNode } from "react";
import { useParams } from "react-router-dom";
import { isUuid } from "@/lib/uuid";
import { NotFoundPage } from "@/pages/system/NotFoundPage";

/** Menampilkan "Tidak ditemukan" bila parameter rute bukan UUID, tanpa memanggil API. */
export function UuidParamGuard({ param = "id", children }: { param?: string; children: ReactNode }) {
  const value = useParams()[param];
  return isUuid(value) ? <>{children}</> : <NotFoundPage />;
}
