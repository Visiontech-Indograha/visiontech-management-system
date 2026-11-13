import { test, expect } from "./fixtures";
import { akun } from "./env";

// Admin awal dibuat lewat halaman penyiapan (/setup) dengan SETUP_TOKEN dari server uji.
// Berjalan pertama (nama berkas 00-). Bila instalasi sudah punya admin, tes dilewati.
const admin = akun("ADMIN");
const token = process.env.E2E_SETUP_TOKEN;

test("penyiapan awal: buat Super Admin lewat /setup lalu masuk", async ({ page }) => {
  test.skip(!admin || !token, "Isi E2E_ADMIN_* dan E2E_SETUP_TOKEN");
  await page.goto("/setup");
  const kode = page.getByLabel("Kode penyiapan");
  const sudah = page.getByText(/sudah disiapkan/);
  await expect(kode.or(sudah)).toBeVisible();
  test.skip(await sudah.isVisible(), "Instalasi uji sudah punya admin (DB belum dikosongkan)");

  // Halaman masuk menautkan ke penyiapan selama belum ada admin.
  await page.goto("/login");
  await expect(page.getByRole("link", { name: "Siapkan akun admin pertama" })).toBeVisible();
  await page.getByRole("link", { name: "Siapkan akun admin pertama" }).click();

  // Sandi kurang dari 12 karakter ditolak di layar.
  await page.getByLabel("Kode penyiapan").fill(token!);
  await page.getByLabel("Nama lengkap").fill("QA-E2E-Admin Awal");
  await page.getByLabel("Email").fill(admin!.email);
  await page.getByLabel("Sandi", { exact: true }).fill("pendek");
  await page.getByLabel("Ulangi sandi").fill("pendek");
  await page.getByRole("button", { name: "Buat akun Super Admin" }).click();
  await expect(page.getByText("Sandi minimal 12 karakter.")).toBeVisible();

  await page.getByLabel("Sandi", { exact: true }).fill(admin!.password);
  await page.getByLabel("Ulangi sandi").fill(admin!.password);
  await page.getByRole("button", { name: "Buat akun Super Admin" }).click();
  await page.waitForURL(/\/login/);

  // Setelah disiapkan, /setup menolak membuat lagi dan tautan di halaman masuk hilang.
  await page.goto("/setup");
  await expect(page.getByText(/sudah disiapkan/)).toBeVisible();
  await page.goto("/login");
  await expect(page.getByRole("link", { name: "Siapkan akun admin pertama" })).toHaveCount(0);
});
