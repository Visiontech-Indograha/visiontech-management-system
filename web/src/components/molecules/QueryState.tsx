import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

interface QueryLike {
  isPending: boolean;
  isError: boolean;
  refetch: () => unknown;
}

/**
 * Keadaan memuat / galat / kosong untuk satu query (docs/11 §8).
 * Contoh: <QueryState query={q} empty={q.data?.length === 0} emptyText="Belum ada SK.">{...}</QueryState>
 */
export function QueryState({
  query,
  errorText,
  empty,
  emptyText,
  emptyAction,
  children,
}: {
  query: QueryLike;
  errorText: string;
  empty?: boolean;
  emptyText?: string;
  emptyAction?: ReactNode;
  children: ReactNode;
}) {
  if (query.isPending)
    return (
      <div aria-hidden className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  if (query.isError)
    return (
      <div role="alert" className="rounded-panel border border-line bg-surface p-6 text-center">
        <p className="mb-3 text-danger">{errorText}</p>
        <Button variant="outline" onClick={() => query.refetch()}>
          Coba lagi
        </Button>
      </div>
    );
  if (empty)
    return (
      <div className="rounded-panel border border-line bg-surface p-6 text-center">
        <p className="mb-3 text-mist">{emptyText}</p>
        {emptyAction}
      </div>
    );
  return <>{children}</>;
}
