import { PageHeader } from "@/components/molecules/PageHeader";

export function ComingSoonPage({ title }: { title: string }) {
  return (
    <>
      <PageHeader title={title} />
      <p className="text-mist">Halaman ini dibangun pada fase berikutnya.</p>
    </>
  );
}
