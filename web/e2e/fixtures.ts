import { test as base, expect } from "@playwright/test";

/**
 * Setiap login membuka satu "perangkat" (batas 4 per akun). Fixture ini keluar lewat UI
 * (Keluar di sidebar, lalu konfirmasi Keluar) bila halaman masih login, dan menunggu kembali ke /login.
 */
export const test = base.extend({
  page: async ({ page }, pakai) => {
    await pakai(page);
    const url = page.url();
    if (url === "about:blank" || /\/(admin-)?login|\/setup/.test(url)) return;
    const keluar = page.getByRole("button", { name: "Keluar", exact: true });
    // Halaman tanpa sidebar (mis. ganti sandi) atau yang sedang memuat: buka Beranda agar tombol Keluar ada.
    if (!(await keluar.isVisible().catch(() => false))) {
      await page.goto("/").catch(() => undefined);
    }
    await keluar.waitFor({ timeout: 10_000 });
    // Tunggu permintaan keluar selesai (hanya mengamati), agar sesi benar-benar dilepas sebelum konteks ditutup.
    const selesai = page.waitForResponse((r) => r.url().includes("/auth/logout"), { timeout: 8000 });
    await keluar.click();
    await page.getByRole("dialog").getByRole("button", { name: "Keluar", exact: true }).click();
    await selesai;
    await page.waitForURL(/login/, { timeout: 8000 });
  },
});

export { expect };
