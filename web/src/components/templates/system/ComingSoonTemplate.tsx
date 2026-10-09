import { ComingSoonNotice } from "@/components/organisms/system/ComingSoonNotice";
import { PageTemplate } from "../PageTemplate";

/** Kerangka halaman menu yang belum dibangun. */
export function ComingSoonTemplate({ title }: { title: string }) {
  return (
    <PageTemplate title={title}>
      <ComingSoonNotice />
    </PageTemplate>
  );
}
