import { useParams, useSearchParams } from "react-router-dom";
import { VerifyTemplate } from "@/components/templates/verify/VerifyTemplate";
import { useVerifyCompletion } from "@/services/exportService";

/** /verify/work-completion/:id?h=<sha256> — isi QR pada BAST resmi (PDF). */
export function VerifyCompletionPage() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const hash = params.get("h") ?? "";
  const query = useVerifyCompletion(id, hash);
  const valid = /^[0-9a-f]{64}$/i.test(hash);
  return <VerifyTemplate data={query.data} pending={valid && query.isPending} failed={!valid || query.isError} />;
}
