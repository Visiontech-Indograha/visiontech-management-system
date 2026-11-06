import { AccountSessionsPanel } from "@/components/organisms/account/AccountSessionsPanel";
import { AccountSummaryCard } from "@/components/organisms/account/AccountSummaryCard";
import { FaceBiometricSection } from "@/components/organisms/account/FaceBiometricSection";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Akun & keamanan": akun + perangkat di kiri, biometrik wajah di kanan (desktop). */
export function AccountTemplate({ email, roleLabel, scopeLines }: { email: string | undefined; roleLabel: string; scopeLines?: string[] }) {
  return (
    <PageTemplate title="Akun & keamanan">
      {/* Desktop: dua kolom (akun + perangkat | biometrik wajah di kanan). Ponsel: satu kolom berurutan akun, wajah, perangkat. */}
      <div className="grid items-start gap-6 lg:grid-cols-2 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
        <AccountSummaryCard email={email} roleLabel={roleLabel} scopeLines={scopeLines} />

        <div className="lg:col-start-2 lg:row-span-2 lg:row-start-1">
          <FaceBiometricSection />
        </div>

        <AccountSessionsPanel />
      </div>
    </PageTemplate>
  );
}
