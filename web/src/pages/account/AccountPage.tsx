import { useSession } from "@/stores/sessionStore";
import { AccountTemplate } from "@/components/templates/account/AccountTemplate";
import { ROLE_LABEL } from "@/lib/types";
import { roleScopeLines } from "@/lib/roleAssignments";


/**
 * Akun & keamanan (M1 / P1-7): ganti sandi dan perangkat yang sedang masuk, termasuk
 * "Keluarkan perangkat lain". Token akses perangkat lain habis paling lama 15 menit.
 */
export function AccountPage() {
  const { me } = useSession();
  return <AccountTemplate email={me?.email} roleLabel={me ? (ROLE_LABEL[me.role] ?? me.role) : ""} scopeLines={roleScopeLines(me)} />;
}
