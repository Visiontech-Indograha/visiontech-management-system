import { useParams } from "react-router-dom";
import { VerificationResultPanel } from "../components/VerificationResultPanel";
import { VerifyIntro } from "../components/VerifyIntro";
import { useVerification } from "../verifyService";

/** PUBLIK (tanpa login): hasil pemindaian QR tanda tangan — GET /verify/{token}. */
export function VerifyPage() {
  const token = useParams()["*"] ?? "";
  const query = useVerification(token);
  return (
    <main className="mx-auto w-full max-w-xl px-4 py-10">
      <VerifyIntro />
      <VerificationResultPanel token={token} query={query} />
    </main>
  );
}
