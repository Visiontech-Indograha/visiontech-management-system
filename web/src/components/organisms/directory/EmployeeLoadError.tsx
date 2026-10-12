import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Galat memuat detail karyawan + tautan kembali ke Direktori. */
export function EmployeeLoadError({ message }: { message: string }) {
  return (
      <div className="mt-16 text-center">
        <TextBlock className="mb-3 text-danger">{message}</TextBlock>
        <InlineLink to="/directory" className="font-semibold text-lens hover:underline">
          Kembali ke Direktori
        </InlineLink>
      </div>
  );
}
