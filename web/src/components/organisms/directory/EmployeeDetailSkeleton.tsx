import { Skeleton } from "@/components/atoms/Skeleton";

/** Kerangka abu-abu selama detail karyawan dimuat. */
export function EmployeeDetailSkeleton() {
  return (
      <div aria-hidden className="max-w-xl space-y-3">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-40 w-full" />
      </div>
  );
}
