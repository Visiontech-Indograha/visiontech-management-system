import { ActionButton } from "@/components/molecules/ActionButton";
import { InlineLink } from "@/components/molecules/Links";

/** Tombol mengambang presentasi: simpan PDF (cetak peramban) + tutup; disembunyikan saat dicetak. */
export function PresentationToolbar({ planId }: { planId: string }) {
  return (
      <div className="fixed bottom-4 left-1/2 z-10 flex -translate-x-1/2 gap-2 md:bottom-auto md:left-auto md:right-4 md:top-4 md:translate-x-0 print:hidden">
        <ActionButton onClick={() => window.print()}>Simpan PDF</ActionButton>
        <ActionButton asChild variant="outline">
          <InlineLink to={`/work-plans/${planId}`}>Tutup presentasi</InlineLink>
        </ActionButton>
      </div>
  );
}
