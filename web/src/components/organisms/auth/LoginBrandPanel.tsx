import logo from "@/assets/brand/logo-visiontech.png";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ImageView } from "@/components/molecules/ImageView";

/** Panel merek di kiri halaman login (hanya desktop) — navy Visiontech + aksen emas. */
export function LoginBrandPanel() {
  return (
      <section aria-hidden className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 -top-24 size-96 rounded-full bg-brand-600/60" />
        <div className="absolute -bottom-32 -left-16 size-80 rounded-full bg-brand-800/70" />
        <div className="relative inline-flex w-fit rounded-panel bg-white px-5 py-3 shadow-card">
          <ImageView src={logo} alt="" className="h-10 w-auto" />
        </div>
        <div className="relative max-w-md">
          <TextBlock as="span" className="mb-4 block h-1 w-12 rounded-full bg-gold" />
          <TextBlock className="text-display text-white">Pekerjaan lapangan, rapi dalam satu tempat.</TextBlock>
          <TextBlock className="mt-3 text-body text-brand-100">Rencana Kerja penugasan, absensi, laporan harian, aset, dan dokumen bertanda tangan digital.</TextBlock>
        </div>
        <TextBlock className="relative text-caption text-brand-200">© PT Visiontech Indograha</TextBlock>
      </section>
  );
}
