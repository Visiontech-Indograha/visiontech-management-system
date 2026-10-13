import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Pesan status sistem di tengah layar (akses ditolak, halaman tidak ditemukan) + tautan kembali ke Beranda. */
export function SystemStatusMessage({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mt-24 text-center">
      <TextBlock as="h1" className="mb-2 text-2xl font-semibold">{title}</TextBlock>
      {description && <TextBlock className="mb-4 text-mist">{description}</TextBlock>}
      <InlineLink to="/" className="font-semibold text-lens hover:underline">
        Kembali ke Beranda
      </InlineLink>
    </div>
  );
}
