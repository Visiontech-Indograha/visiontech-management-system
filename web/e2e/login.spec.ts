import { test, expect } from "@playwright/test";
import { akun } from "./env";
import { masukLewatUI } from "./helpers";

const a = akun("STAFF") ?? akun("ADMIN");

test.describe("login", () => {
  test.skip(!a, "Isi E2E_STAFF_EMAIL/E2E_STAFF_PASSWORD (atau ADMIN)");

  test("sandi benar masuk ke aplikasi", async ({ page }) => {
    await masukLewatUI(page, a!, !akun("STAFF"));
    await expect(page).not.toHaveURL(/\/login/);
  });

  test("sandi salah (sekali saja) ditolak dengan pesan", async ({ page }) => {
    // Hanya SATU percobaan gagal agar akun tidak terkunci.
    await masukLewatUI(page, { email: a!.email, password: a!.password + "-salah" }, !akun("STAFF"));
    await expect(page.getByTestId("login-error")).toBeVisible();
    await expect(page).toHaveURL(/login/);
  });
});
