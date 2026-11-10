import { test, expect } from "./fixtures";
import { akun, type Peran } from "./env";
import { masukLewatUI } from "./helpers";

// Menu yang harus ada / tidak ada per peran (mengikuti web/src/app/navigation.ts).
const KASUS: { peran: Peran; ada: string[]; tidakAda: string[] }[] = [
  { peran: "STAFF", ada: ["Absensi", "Cuti dan Izin"], tidakAda: ["Audit log"] },
  { peran: "ADMIN", ada: ["Absensi", "Cuti dan Izin", "Audit log", "Direktori"], tidakAda: [] },
];

for (const k of KASUS) {
  test(`menu peran ${k.peran}`, async ({ page }) => {
    const a = akun(k.peran);
    test.skip(!a, `Isi E2E_${k.peran}_EMAIL/E2E_${k.peran}_PASSWORD`);
    await masukLewatUI(page, a!, k.peran === "ADMIN");
    await expect(page).not.toHaveURL(/login/);
    for (const m of k.ada) await expect(page.getByRole("link", { name: m }).first()).toBeAttached();
    for (const m of k.tidakAda) await expect(page.getByRole("link", { name: m })).toHaveCount(0);
  });
}
