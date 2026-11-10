import { test, expect } from "@playwright/test";
import { akun } from "./env";
import { masukLewatUI, tanggalWib } from "./helpers";

const admin = akun("ADMIN");

test("absensi: filter tanggal memuat ulang daftar tanpa galat", async ({ page }) => {
  test.skip(!admin, "Isi E2E_ADMIN_*");
  await masukLewatUI(page, admin!, true);
  await page.goto("/attendance");
  await page.getByLabel("Dari tanggal").fill(tanggalWib(-7));
  await page.getByLabel("Sampai tanggal").fill(tanggalWib(0));
  await expect(page.getByLabel("Dari tanggal")).toHaveValue(tanggalWib(-7));
  await expect(page.getByText(/Terjadi kesalahan|Gagal memuat/i)).toHaveCount(0);
});

test("rekap absensi bulanan tampil", async ({ page }) => {
  test.skip(!admin, "Isi E2E_ADMIN_*");
  await masukLewatUI(page, admin!, true);
  await page.goto("/attendance-recap");
  await expect(page.getByRole("heading").first()).toBeVisible();
  await expect(page.getByText(/Terjadi kesalahan|Gagal memuat/i)).toHaveCount(0);
});
