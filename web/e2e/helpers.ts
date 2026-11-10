import { type Page } from "@playwright/test";
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
