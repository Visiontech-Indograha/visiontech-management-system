import { test, expect } from "./fixtures";
import { akun, PREFIX } from "./env";
import { buatStafLewatUI, hapusKaryawanLewatUI, hariKerja, masukLewatUI } from "./helpers";

// Staf kantor (peran HR/GA, diberi admin lewat kartu akun) mengajukan cuti lalu membatalkannya selagi
// menunggu. Data uji dibersihkan admin lewat UI (hapus karyawan).
test("ajukan cuti lalu batalkan pengajuan yang masih menunggu, semuanya lewat UI", async ({ page }) => {
  const a = akun("ADMIN");
  test.skip(!a, "Isi E2E_ADMIN_*");
  test.setTimeout(240_000);
  await masukLewatUI(page, a!, true);
  const staf = await buatStafLewatUI(page, "HR/GA", PREFIX);
  try {
    await page.getByRole("button", { name: "Keluar", exact: true }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Keluar", exact: true }).click();
    await page.waitForURL(/login/);
    await masukLewatUI(page, { email: staf.email, password: staf.sandiSementara }, false, false);
    await page.waitForURL(/change-password/);
    const baru = `${PREFIX}Baru-${Date.now()}`;
    await page.getByLabel("Sandi saat ini").fill(staf.sandiSementara);
    await page.getByLabel("Sandi baru", { exact: true }).fill(baru);
    await page.getByLabel("Ulangi sandi baru").fill(baru);
    await page.locator("form").getByRole("button").last().click();
    await page.waitForURL((u) => !/change-password/.test(u.pathname));

    await page.goto("/leaves");
    await page.getByRole("button", { name: "Ajukan cuti / izin" }).click();
    const dlg = page.getByRole("dialog");
    const tgl = hariKerja(14);
    await dlg.getByLabel("Tanggal Mulai").fill(tgl);
    await dlg.getByLabel("Tanggal Selesai").fill(tgl);
    await dlg.getByLabel("Alasan Pengajuan").fill(`${PREFIX}uji batal pengajuan`);
    await dlg.getByRole("button", { name: "Kirim Pengajuan" }).click();
    await expect(dlg).toBeHidden();
    // Pengajuan baru berstatus menunggu: tombol batal untuk pemilik muncul.
    await expect(page.getByRole("button", { name: /Batalkan pengajuan/ }).first()).toBeVisible();

    // Batalkan pengajuan: ada konfirmasi dulu, lalu status berubah.
    await page.getByRole("button", { name: /Batalkan pengajuan/ }).first().click();
    await page.getByRole("dialog").getByRole("button", { name: "Ya, batalkan" }).click();
    await expect(page.getByText("Pengajuan dibatalkan.")).toBeVisible();
    await expect(page.getByRole("button", { name: /Batalkan pengajuan/ })).toHaveCount(0);
  } finally {
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
