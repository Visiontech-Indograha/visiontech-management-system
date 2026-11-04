import { Skeleton } from "@/components/atoms/Skeleton";
import { Text } from "@/components/atoms/Text";

/** Kerangka pemuat halaman penuh (pengganti teks "Memuat..."). */
export function PageSkeleton({ label = "Sedang memuat halaman" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-4 p-6">
      <Text className="sr-only">{label}</Text>
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-4 w-80 max-w-full" />
      <div className="grid gap-3 md:grid-cols-2">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}
