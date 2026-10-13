import type { ComponentProps } from "react";
import { Skeleton } from "../atoms/Skeleton";

/** Batang abu-abu saat memuat. Contoh: <LoadingBar className="h-24" /> */
export function LoadingBar(props: ComponentProps<typeof Skeleton>) {
  return <Skeleton {...props} />;
}
