import { Link } from "react-router-dom";
import { Button } from "@/components/atoms/Button";

/** Kartu akun: email, peran, tautan ganti password. */
export function AccountSummaryCard({ email, roleLabel }: { email: string | undefined; roleLabel: string }) {
  return (
        <section aria-label="Akun" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
          <p className="font-medium">{email}</p>
          <p className="mb-4 text-sm text-mist">{roleLabel}</p>
          <Button asChild variant="outline">
            <Link to="/change-password">Ganti password</Link>
          </Button>
        </section>
  );
}
