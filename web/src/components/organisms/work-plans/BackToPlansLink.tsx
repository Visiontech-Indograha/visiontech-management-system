import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Tautan kembali ke daftar rencana kerja. */
export function BackToPlansLink() {
  return (
      <TextBlock className="mt-6">
        <InlineLink to="/work-plans" className="font-semibold text-lens hover:underline">
          Kembali ke daftar work plan
        </InlineLink>
      </TextBlock>
  );
}
