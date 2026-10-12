import { ActionButton } from "@/components/molecules/ActionButton";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Kartu akun: email, peran, tautan ganti password. */
export function AccountSummaryCard({ email, roleLabel }: { email: string | undefined; roleLabel: string }) {
  return (
        <section aria-label="Akun" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
          <TextBlock className="font-medium">{email}</TextBlock>
          <TextBlock className="mb-4 text-sm text-mist">{roleLabel}</TextBlock>
          <ActionButton asChild variant="outline">
            <InlineLink to="/change-password">Ganti password</InlineLink>
          </ActionButton>
        </section>
  );
}
