import { LoadingBar } from "@/components/molecules/LoadingBar";

/** Kerangka abu-abu selama data presentasi dimuat. */
export function PresentationSkeleton() {
  return (
    <>
        <LoadingBar className="h-10 w-2/3" />
        <LoadingBar className="h-64 w-full" />
    </>
  );
}
