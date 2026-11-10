import { test, expect } from "./fixtures";
import { akun } from "./env";
import { masukLewatUI } from "./helpers";

const a = akun("ADMIN");

test.describe("login", () => {
  test.skip(!a, "Isi E2E_ADMIN_EMAIL/E2E_ADMIN_PASSWORD");

  test("sandi benar masuk ke aplikasi", async ({ page }) => {
    await masukLewatUI(page, a!, true);
    await expect(page).not.toHaveURL(/\/login/);
  });

  test("sandi salah (sekali saja) ditolak dengan pesan", async ({ page }) => {
    // Hanya SATU percobaan gagal agar akun tidak terkunci.
    await masukLewatUI(page, { email: a!.email, password: a!.password + "-salah" }, true, false);
    await expect(page.getByTestId("login-error")).toBeVisible();
    await expect(page.getByTestId("login-error")).not.toBeEmpty();
    await expect(page).toHaveURL(/login/);
  });
});
