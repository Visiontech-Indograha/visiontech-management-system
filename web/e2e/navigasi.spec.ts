import { test, expect } from "./fixtures";
import { akun } from "./env";
import { masukLewatUI } from "./helpers";

// Menu yang harus ada per peran (mengikuti web/src/app/navigation.ts).
test("menu peran ADMIN", async ({ page }) => {
  const a = akun("ADMIN");
  test.skip(!a, "Isi E2E_ADMIN_EMAIL/E2E_ADMIN_PASSWORD");
  await masukLewatUI(page, a!, true);
  await expect(page).not.toHaveURL(/login/);
  for (const m of ["Absensi", "Cuti dan Izin", "Audit log", "Direktori"]) {
    await expect(page.getByRole("link", { name: m }).first()).toBeAttached();
  }
});

test.fixme(
  "menu peran STAFF (kantor biasa)",
  async () => {
    // jalur UI belum ada: pemberian peran kantor ke akun baru (flag ROLE_ASSIGNMENT_ENABLED tidak bisa
    // diaktifkan dari UI). Layar: Direktori > Akun login > Peran. Peran yang berhak: SUPER_ADMIN.
  },
);
