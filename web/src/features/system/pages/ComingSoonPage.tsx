import { PageTemplate } from "@/components/templates/PageTemplate";
import { ComingSoonNotice } from "../components/ComingSoonNotice";

/** Halaman sementara untuk menu yang belum dibangun. */
export function ComingSoonPage({ title }: { title: string }) {
  return (
    <PageTemplate title={title}>
      <ComingSoonNotice />
    </PageTemplate>
  );
}
