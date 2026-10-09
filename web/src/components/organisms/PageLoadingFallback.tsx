import { Skeleton } from "../atoms/Skeleton";

/** Kerangka abu-abu selama halaman (lazy) dimuat — dipakai `AppShell` sebagai fallback `Suspense`. */
export function PageLoadingFallback() {
  return (
    <div aria-busy className="space-y-4">
      <Skeleton className="h-9 w-64" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}
