import { LoadingBar } from "@/components/molecules/LoadingBar";

/** Kerangka abu-abu selama halaman (lazy) dimuat — dipakai `AppShell` sebagai fallback `Suspense`. */
export function PageLoadingFallback() {
  return (
    <div aria-busy className="space-y-4">
      <LoadingBar className="h-9 w-64" />
      <LoadingBar className="h-40 w-full" />
    </div>
  );
}
