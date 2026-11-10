import { expect, type Page } from "@playwright/test";
import { type Akun } from "./env";

/** `tunggu=false` untuk uji login gagal (tidak menunggu pindah halaman). */
export async function masukLewatUI(page: Page, a: Akun, admin = false, tunggu = true) {
  await page.goto(admin ? "/admin-login" : "/login");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Email").fill(a.email);
  await page.getByLabel("Sandi", { exact: true }).fill(a.password);
  await page.getByRole("button", { name: "Masuk" }).click();
  if (tunggu) await page.waitForURL((u) => !/login/.test(u.pathname));
}

/** Tanggal (WIB) hari kerja Senin-Jumat, mulai dari offset hari lalu maju bila jatuh di akhir pekan. */
export function hariKerja(offsetHari: number): string {
  let o = offsetHari;
  for (;;) {
    const t = tanggalWib(o);
    const hari = new Date(`${t}T00:00:00Z`).getUTCDay();
    if (hari !== 0 && hari !== 6) return t;
    o += 1;
  }
}

export function tanggalWib(offsetHari = 0): string {
  const d = new Date(Date.now() + 7 * 3600_000 + offsetHari * 86400_000);
  return d.toISOString().slice(0, 10);
}

export type Staf = { nama: string; email: string; urlKaryawan: string; sandiSementara: string };

/**
 * Admin (sudah masuk) membuat karyawan + akun lewat UI, memberi peran utama kantor lewat kartu akun
 * (dengan konfirmasi), lalu mereset sandi agar akun wajib ganti sandi saat masuk. Mengembalikan sandi sementara.
 */
export async function buatStafLewatUI(page: Page, peranLabel: string, prefix: string): Promise<Staf> {
  const nomor = `${prefix}${Date.now()}`;
  const nama = `${prefix}Staf Uji`;
  const email = `${nomor.toLowerCase()}@visiontech.id`;
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
  await page.getByLabel("Email login").fill(email);
  await page.getByRole("button", { name: "Buat akun" }).click();
  await page.getByLabel("Peran utama").waitFor();
  await page.getByLabel("Peran utama").selectOption({ label: peranLabel });
  await page.getByRole("button", { name: "Simpan peran" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Ya, ubah peran" }).click();
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  // Sandi dari pembuatan akun masih tampil; tunggu sampai berganti oleh hasil reset.
  const sandiAwal = (await page.locator("code").first().innerText()).trim();
  await page.getByRole("button", { name: "Reset sandi" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Ya, reset sandi" }).click();
  await expect(page.locator("code").first()).not.toHaveText(sandiAwal);
  const sandiSementara = (await page.locator("code").first().innerText()).trim();
  return { nama, email, urlKaryawan, sandiSementara };
}

/** Pembersihan lewat UI: hapus akun, offboarding (mulai, setujui PM, setujui HR), hapus karyawan permanen. */
export async function hapusKaryawanLewatUI(page: Page, urlKaryawan: string, nama: string) {
  await page.goto(urlKaryawan);
  const hapusAkun = page.getByRole("button", { name: "Hapus akun login" });
  if (await hapusAkun.isVisible().catch(() => false)) {
    await hapusAkun.click();
    await page.getByLabel("Ketik HAPUS untuk melanjutkan").fill("HAPUS");
    await page.getByRole("dialog").getByRole("button", { name: "Hapus permanen" }).click();
    await page.getByText("Karyawan ini belum punya akun login.").waitFor();
  }
  await page.goto(urlKaryawan);
  await page.getByRole("button", { name: "Offboarding", exact: true }).click();
  await page.getByRole("dialog").getByLabel("Tanggal efektif").fill(tanggalWib(0));
  await page.getByRole("button", { name: "Mulai offboarding" }).click();
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  await page.goto("/offboarding");
  await page.getByRole("button", { name: new RegExp(nama) }).first().click();
  for (const peran of ["PM", "HR"]) {
    await page.getByRole("button", { name: `Setujui sebagai ${peran}` }).click();
    await page.getByRole("dialog").last().getByRole("button", { name: "Setujui", exact: true }).click();
    await page.getByText(peran === "PM" ? /PM\/OM: (?!belum)/ : /HR: (?!belum)/).first().waitFor();
  }
  await page.goto(urlKaryawan);
  await page.getByRole("button", { name: "Hapus karyawan", exact: true }).click();
  await page.getByRole("button", { name: "Ya, hapus" }).click();
  await page.getByRole("button", { name: "Hapus permanen", exact: true }).first().click();
  await page.getByLabel("Ketik HAPUS untuk melanjutkan").fill("HAPUS");
  await page.getByRole("dialog").getByRole("button", { name: "Hapus permanen" }).click();
  await page.waitForURL(/\/directory$/);
}
