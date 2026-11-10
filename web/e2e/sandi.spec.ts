import { test, expect } from "./fixtures";
import { akun, API_URL, PREFIX } from "./env";
import { bearer, masukLewatUI, tanggalWib, tokenApi } from "./helpers";

const staff = akun("STAFF");
const admin = akun("ADMIN");

test("ganti sandi: sandi baru sama dengan sandi lama ditolak", async ({ page }) => {
  test.skip(!staff, "Isi E2E_STAFF_*");
  await masukLewatUI(page, staff!);
  await page.goto("/change-password");
  await page.getByLabel("Sandi saat ini").fill(staff!.password);
  await page.getByLabel("Sandi baru", { exact: true }).fill(staff!.password);
  await page.getByLabel("Ulangi sandi baru").fill(staff!.password);
  await page.locator("form").getByRole("button").last().click();
  // Tetap di halaman ganti sandi (ditolak), sandi tidak berubah.
  await expect(page).toHaveURL(/change-password/);
});

test("admin mereset sandi karyawan (reset-password) lewat UI", async ({ page, request }) => {
  test.skip(!admin, "Isi E2E_ADMIN_*");
  const h = bearer(await tokenApi(request, admin!));
  const o = await (await request.get(`${API_URL}/offices`, { headers: h })).json();
  const daftar = (Array.isArray(o) ? o : o.items) as Record<string, string>[];
  const officeId = daftar[0].office_id ?? daftar[0].id;
  const nomor = `${PREFIX}${Date.now()}`;
  const emp = await request.post(`${API_URL}/employees`, {
    headers: h,
    data: { employee_no: nomor, full_name: `${PREFIX}Karyawan Uji`, office_id: officeId, join_date: tanggalWib(0) },
  });
  expect(emp.ok()).toBeTruthy();
  const eb = (await emp.json()) as Record<string, string>;
  const empId = eb.employee_id ?? eb.id;
  try {
    const ak = await request.post(`${API_URL}/employees/${empId}/account`, {
      headers: h,
      data: { login: `${nomor.toLowerCase()}@visiontech.id`, system_role: "EMPLOYEE" },
    });
    expect(ak.ok()).toBeTruthy();

    await masukLewatUI(page, admin!, true);
    await page.goto(`/directory/${empId}`);
    await page.getByRole("button", { name: "Reset sandi" }).click();
    await expect(page.getByText(/Sandi sementara/)).toBeVisible();
  } finally {
    await request.delete(`${API_URL}/employees/${empId}/account`, { headers: h });
    await request.delete(`${API_URL}/employees/${empId}`, { headers: h });
  }
});
