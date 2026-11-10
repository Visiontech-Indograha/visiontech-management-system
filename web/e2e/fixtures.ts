import { test as base, expect } from "@playwright/test";

/**
 * Setiap login membuka satu "perangkat" (batas 4 per akun). Fixture ini keluar lewat UI
 * (Keluar di sidebar, lalu konfirmasi Keluar) bila halaman masih login, dan menunggu kembali ke /login.
 */
export const test = base.extend({
  page: async ({ page }, pakai) => {
    await pakai(page);
    const keluar = page.getByRole("button", { name: "Keluar", exact: true });
    if (await keluar.isVisible().catch(() => false)) {
      await keluar.click();
      // Tunggu permintaan keluar selesai (hanya mengamati), agar sesi benar-benar dilepas sebelum konteks ditutup.
      const selesai = page.waitForResponse((r) => r.url().includes("/auth/logout"), { timeout: 8000 });
      await page.getByRole("dialog").getByRole("button", { name: "Keluar", exact: true }).click();
      await selesai;
      await page.waitForURL(/login/, { timeout: 8000 });
    }
  },
});

export { expect };
