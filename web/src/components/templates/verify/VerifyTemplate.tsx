import { CompletionVerificationCard, VerifyHeading } from "@/components/organisms/verify/CompletionVerificationCard";
import type { CompletionVerification } from "@/services/exportService";

/** Kerangka halaman publik verifikasi dokumen (dibuka dari QR, tanpa login). */
export function VerifyTemplate(props: { data: CompletionVerification | undefined; pending: boolean; failed: boolean }) {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-4 px-4 py-8">
      <header>
        <VerifyHeading />
      </header>
      <CompletionVerificationCard {...props} />
    </main>
  );
}
