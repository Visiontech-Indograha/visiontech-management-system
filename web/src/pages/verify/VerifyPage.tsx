import { useParams } from "react-router-dom";
import { VerifyTemplate } from "@/components/templates/verify/VerifyTemplate";
import { useVerification } from "@/services/verifyService";

/** PUBLIK (tanpa login): hasil pemindaian QR tanda tangan — GET /verify/{token}. */
export function VerifyPage() {
  const token = useParams()["*"] ?? "";
  const query = useVerification(token);
  return <VerifyTemplate token={token} query={query} />;
}
