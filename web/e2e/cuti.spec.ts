import { test, expect } from "./fixtures";
import { akun, API_URL, PREFIX } from "./env";
import { bearer, hariKerja, masukLewatUI, tokenApi } from "./helpers";

const staff = akun("STAFF");
const admin = akun("ADMIN");

test("ajukan cuti lalu ditinjau (disetujui) dan dibersihkan", async ({ page, browser, request }) => {
  test.skip(!staff || !admin, "Butuh E2E_STAFF_* dan E2E_ADMIN_*");
  const alasan = `${PREFIX}cuti ${Date.now()}`;
  // Tanggal acak dalam tahun berjalan (daftar cuti memfilter tahun ini) agar tidak bentrok antar-run.
  const mulai = hariKerja(15 + Math.floor(Math.random() * 18));
  try {
    await masukLewatUI(page, staff!);
    await page.goto("/leaves");
    await page.getByRole("button", { name: "Ajukan cuti / izin" }).first().click();
    await page.getByLabel("Jenis Cuti / Izin").selectOption("OTHER");
    await page.getByLabel("Tanggal Mulai").fill(mulai);
    await page.getByLabel("Tanggal Selesai").fill(mulai);
    await page.getByLabel("Alasan Pengajuan").fill(alasan);
    await page.getByRole("button", { name: "Kirim Pengajuan" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();

    // Tinjau lewat UI oleh admin/HR di sesi terpisah.
    const ctx = await browser.newContext();
    const p2 = await ctx.newPage();
    await masukLewatUI(p2, admin!, true);
    await p2.goto("/leaves");
    await p2.getByRole("button", { name: "Tinjau cuti QA-E2E-Staf Uji" }).first().click({ timeout: 8000 });
    await expect(p2.getByRole("dialog")).toContainText("Tinjau Permohonan Cuti");
    await p2.getByRole("button", { name: "Setujui Permohonan" }).click();
    await expect(p2.getByRole("dialog")).toBeHidden();
    await ctx.request.post(`${API_URL}/auth/logout`, { timeout: 3000 }).catch(() => undefined);
    await ctx.close();
  } finally {
    // Bersihkan: batalkan cuti QA-E2E- milik staf.
    const t = await tokenApi(request, staff!);
    const r = await request.get(`${API_URL}/leaves?q=${encodeURIComponent(PREFIX)}`, { headers: bearer(t) });
    const items = r.ok() ? ((await r.json()) as { leave_id: string; reason: string }[]) : [];
    for (const l of items.filter((x) => x.reason?.startsWith(PREFIX))) {
      await request.post(`${API_URL}/leaves/${l.leave_id}/cancel`, {
        headers: bearer(t),
        data: { reason: "Pembersihan QA-E2E" },
      });
    }
  }
});
