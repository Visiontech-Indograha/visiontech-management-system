import { Skeleton } from "@/components/atoms/Skeleton";

/** Kerangka abu-abu selama data presentasi dimuat. */
export function PresentationSkeleton() {
  return (
    <>
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-64 w-full" />
    </>
  );
}
