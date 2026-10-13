import { LoadingBar } from "@/components/molecules/LoadingBar";

/** Kerangka abu-abu selama detail karyawan dimuat. */
export function EmployeeDetailSkeleton() {
  return (
      <div aria-hidden className="max-w-xl space-y-3">
        <LoadingBar className="h-8 w-1/2" />
        <LoadingBar className="h-40 w-full" />
      </div>
  );
}
