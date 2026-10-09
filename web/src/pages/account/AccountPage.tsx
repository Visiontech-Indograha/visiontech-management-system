import { useSession } from "@/app/session";
import { AccountSessionsPanel } from "@/components/organisms/account/AccountSessionsPanel";
import { AccountSummaryCard } from "@/components/organisms/account/AccountSummaryCard";
import { FaceBiometricSection } from "@/components/organisms/account/FaceBiometricSection";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { ROLE_LABEL } from "@/lib/types";

/**
 * Akun & keamanan (M1 / P1-7): ganti password dan perangkat yang sedang masuk, termasuk
 * "Keluarkan perangkat lain". Token akses perangkat lain habis paling lama 15 menit.
 */
export function AccountPage() {
  const { me } = useSession();

  return (
    <PageTemplate title="Akun & keamanan">
      {/* Desktop: dua kolom (akun + perangkat | biometrik wajah di kanan). Ponsel: satu kolom berurutan akun, wajah, perangkat. */}
      <div className="grid items-start gap-6 lg:grid-cols-2 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
        <AccountSummaryCard email={me?.email} roleLabel={me ? (ROLE_LABEL[me.role] ?? me.role) : ""} />

        <div className="lg:col-start-2 lg:row-span-2 lg:row-start-1">
          <FaceBiometricSection />
        </div>

        <AccountSessionsPanel />
      </div>
    </PageTemplate>
  );
}
