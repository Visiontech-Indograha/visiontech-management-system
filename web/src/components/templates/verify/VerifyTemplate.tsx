import type { UseQueryResult } from "@tanstack/react-query";
import { VerificationResultPanel } from "@/components/organisms/verify/VerificationResultPanel";
import { VerifyIntro } from "@/components/organisms/verify/VerifyIntro";
import type { VerifyOut } from "@/services/verifyService";

/** Kerangka publik verifikasi tanda tangan QR. */
export function VerifyTemplate({ token, query }: { token: string; query: UseQueryResult<VerifyOut> }) {
  return (
    <main className="mx-auto w-full max-w-xl px-4 py-10">
      <VerifyIntro />
      <VerificationResultPanel token={token} query={query} />
    </main>
  );
}
