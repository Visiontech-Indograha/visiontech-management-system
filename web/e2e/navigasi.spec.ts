import { test, expect } from "./fixtures";
import { akun, PREFIX } from "./env";
import { buatStafLewatUI, hapusKaryawanLewatUI, masukLewatUI } from "./helpers";

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

test("menu peran kantor (HR/GA): peran diberi admin lewat kartu akun, sandi sementara wajib diganti", async ({ page }) => {
  const a = akun("ADMIN");
  test.skip(!a, "Isi E2E_ADMIN_EMAIL/E2E_ADMIN_PASSWORD");
  test.setTimeout(180_000);
  await masukLewatUI(page, a!, true);
  const staf = await buatStafLewatUI(page, "HR/GA", PREFIX);
  try {
    // Keluar sebagai admin (lewat UI), lalu masuk sebagai staf dengan sandi sementara.
    await page.getByRole("button", { name: "Keluar", exact: true }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Keluar", exact: true }).click();
    await page.waitForURL(/login/);
    await masukLewatUI(page, { email: staf.email, password: staf.sandiSementara }, false, false);

    // Wajib ganti sandi: halaman lain tertutup sampai sandi diganti.
    await page.waitForURL(/change-password/);
    await page.goto("/directory");
    await expect(page).toHaveURL(/change-password/);
    const baru = `${PREFIX}Baru-${Date.now()}`;
    await page.getByLabel("Sandi saat ini").fill(staf.sandiSementara);
    await page.getByLabel("Sandi baru", { exact: true }).fill(baru);
    await page.getByLabel("Ulangi sandi baru").fill(baru);
    await page.locator("form").getByRole("button").last().click();
    await page.waitForURL((u) => !/change-password/.test(u.pathname));

    for (const m of ["Absensi", "Cuti dan Izin", "Direktori"]) {
      await expect(page.getByRole("link", { name: m }).first()).toBeAttached();
    }
    await expect(page.getByRole("link", { name: "Audit log" })).toHaveCount(0);
  } finally {
    // Keluar sebagai staf bila masih masuk, lalu bersihkan sebagai admin.
    const keluar = page.getByRole("button", { name: "Keluar", exact: true });
    if (await keluar.isVisible().catch(() => false)) {
      await keluar.click();
      await page.getByRole("dialog").getByRole("button", { name: "Keluar", exact: true }).click();
      await page.waitForURL(/login/);
    }
    await masukLewatUI(page, a!, true);
    await hapusKaryawanLewatUI(page, staf.urlKaryawan, staf.nama);
  }
});
