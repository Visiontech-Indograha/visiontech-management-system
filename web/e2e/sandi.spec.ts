import { test, expect } from "./fixtures";
import { akun, PREFIX } from "./env";
import { masukLewatUI, tanggalWib } from "./helpers";

const admin = akun("ADMIN");

test("ganti sandi: sandi baru sama dengan sandi lama ditolak dengan pesan", async ({ page }) => {
  test.skip(!admin, "Isi E2E_ADMIN_*");
  await masukLewatUI(page, admin!, true);
  await page.goto("/change-password");
  await page.getByLabel("Sandi saat ini").fill(admin!.password);
  await page.getByLabel("Sandi baru", { exact: true }).fill(admin!.password);
  await page.getByLabel("Ulangi sandi baru").fill(admin!.password);
  await page.locator("form").getByRole("button").last().click();
  await expect(page).toHaveURL(/change-password/);
  // Pesan galat harus tampil di layar (bukan hanya tetap di halaman).
  await expect(page.getByText(/sandi baru.*(berbeda|sama)|(berbeda|sama).*sandi/i).first()).toBeVisible();
});

test("ganti sandi: sandi saat ini salah ditolak dengan pesan", async ({ page }) => {
  test.skip(!admin, "Isi E2E_ADMIN_*");
  await masukLewatUI(page, admin!, true);
  await page.goto("/change-password");
  await page.getByLabel("Sandi saat ini").fill(admin!.password + "-salah");
  await page.getByLabel("Sandi baru", { exact: true }).fill(admin!.password + "-Baru1");
  await page.getByLabel("Ulangi sandi baru").fill(admin!.password + "-Baru1");
  await page.locator("form").getByRole("button").last().click();
  await expect(page).toHaveURL(/change-password/);
  await expect(page.getByText(/sandi.*(salah|tidak benar|tidak sesuai|keliru)/i).first()).toBeVisible();
});

test("admin membuat karyawan dan akun, mereset sandi, lalu menghapus semuanya lewat UI", async ({ page }) => {
  test.skip(!admin, "Isi E2E_ADMIN_*");
  test.setTimeout(150_000);
  const nomor = `${PREFIX}${Date.now()}`;
  const nama = `${PREFIX}Karyawan Uji`;
  await masukLewatUI(page, admin!, true);

  await page.goto("/directory");
  await page.getByRole("button", { name: "Tambah karyawan" }).click();
  const dlg = page.getByRole("dialog");
  await dlg.getByLabel("No. karyawan").fill(nomor);
  await dlg.getByLabel("Nama lengkap").fill(nama);
  await dlg.getByLabel("Kantor").selectOption({ index: 1 });
  await dlg.getByLabel("Tanggal bergabung").fill(tanggalWib(0));
  await dlg.getByRole("button", { name: "Simpan" }).click();
  await page.waitForURL(/\/directory\/[0-9a-f-]{36}/);
  const urlKaryawan = new URL(page.url()).pathname;

  try {
    await page.getByLabel("Email login").fill(`${nomor.toLowerCase()}@visiontech.id`);
    await page.getByRole("button", { name: "Buat akun" }).click();
    await expect(page.getByText("Aktif", { exact: true }).first()).toBeVisible();

    await page.getByRole("button", { name: "Reset sandi" }).click();
    await expect(page.getByText(/Sandi sementara/)).toBeVisible();
  } finally {
    // Pembersihan lewat UI: hapus akun, hapus karyawan, hapus permanen.
    const hapusAkun = page.getByRole("button", { name: "Hapus akun login" });
    if (await hapusAkun.isVisible().catch(() => false)) {
      await hapusAkun.click();
      await page.getByLabel("Ketik HAPUS untuk melanjutkan").fill("HAPUS");
      await page.getByRole("dialog").getByRole("button", { name: "Hapus permanen" }).click();
      await expect(page.getByText("Karyawan ini belum punya akun login.")).toBeVisible();
    }
    // Karyawan baru boleh dihapus setelah offboarding selesai (mulai, setujui PM, setujui HR).
    await page.goto(urlKaryawan);
    await page.getByRole("button", { name: "Offboarding", exact: true }).click();
    await page.getByRole("dialog").getByLabel("Tanggal efektif").fill(tanggalWib(0));
    await page.getByRole("button", { name: "Mulai offboarding" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();
    await page.goto("/offboarding");
    await page.getByRole("button", { name: new RegExp(nama) }).first().click();
    for (const peran of ["PM", "HR"]) {
      await page.getByRole("button", { name: `Setujui sebagai ${peran}` }).click();
      await page.getByRole("dialog").last().getByRole("button", { name: "Setujui", exact: true }).click();
      await expect(page.getByText(peran === "PM" ? /PM\/OM: (?!belum)/ : /HR: (?!belum)/).first()).toBeVisible();
    }
    await page.goto(urlKaryawan);
    await page.getByRole("button", { name: "Hapus karyawan", exact: true }).click();
    await page.getByRole("button", { name: "Ya, hapus" }).click();
    await page.getByRole("button", { name: "Hapus permanen", exact: true }).first().click();
    await page.getByLabel("Ketik HAPUS untuk melanjutkan").fill("HAPUS");
    await page.getByRole("dialog").getByRole("button", { name: "Hapus permanen" }).click();
    await expect(page).toHaveURL(/\/directory$/);
  }
});
