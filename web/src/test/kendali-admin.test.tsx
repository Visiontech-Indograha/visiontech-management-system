import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { apiError, mockApi, renderRoute } from "./utils";

/** Kendali admin atas akun karyawan (HR/SUPER_ADMIN) + petunjuk di halaman login. */

const ID = "00000000-0000-4000-8000-0000000000e1";
const ACCOUNT = `/employees/${ID}/account`;
const employee = () => ({
  employee_id: ID, employee_no: "VT-001", full_name: "Test User", office_id: "o1", office_name: "Kantor Pusat",
  division_id: "u1", division_name: "CCTV & ACS", position_id: "p1", position_code: "TEK", position_name: "Teknisi",
  join_date: "2024-01-01", pkwt_end_date: null, photo_file_id: null, face_enrolled: false,
  offboarding_status: "active", archived: false, email: null, addresses: [],
});
const future = () => new Date(Date.now() + 10 * 60_000).toISOString();

/** Pengguna HR yang juga punya izin hapus permanen (SUPER_ADMIN) untuk menguji zona berbahaya. */
const superAdmin = () => ({ ...mockMe("HR")!, permissions: [...mockMe("HR")!.permissions, "delete:any"] });

describe("akun karyawan: buka kunci & status terkunci (HR)", () => {
  it("akun terkunci menampilkan status dan tombol buka kunci yang memanggil API", async () => {
    let locked = true;
    const calls = mockApi((c) => {
      if (c.url === `/employees/${ID}`) return { data: employee() };
      if (c.url === "/employees/" + ID + "/documents") return { data: { items: [], total: 0 } };
      if (c.url === ACCOUNT && c.method === "get")
        return { data: { exists: true, login: "a@contoh.id", is_active: true, system_role: "EMPLOYEE",
          failed_logins: 5, locked_until: locked ? future() : null } };
      if (c.url === `${ACCOUNT}/sessions`) return { data: [] };
      if (c.url === `${ACCOUNT}/unlock`) {
        locked = false;
        return { data: { exists: true, login: "a@contoh.id", is_active: true, system_role: "EMPLOYEE", failed_logins: 0, locked_until: null } };
      }
    });
    renderRoute(`/directory/${ID}`, { role: "HR" });
    expect(await screen.findByTestId("account-locked")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Buka kunci akun" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === `${ACCOUNT}/unlock`)).toBe(true));
  });

  it("HR tanpa izin hapus permanen tidak melihat zona berbahaya", async () => {
    mockApi((c) => {
      if (c.url === `/employees/${ID}`) return { data: employee() };
      if (c.url === `/employees/${ID}/documents`) return { data: { items: [], total: 0 } };
      if (c.url === ACCOUNT) return { data: { exists: true, login: "a@contoh.id", is_active: true, system_role: "EMPLOYEE", failed_logins: 0, locked_until: null } };
      if (c.url === `${ACCOUNT}/sessions`) return { data: [] };
    });
    renderRoute(`/directory/${ID}`, { role: "HR" });
    await screen.findByText("Perangkat yang masuk");
    expect(screen.queryByText("Zona berbahaya")).toBeNull();
    expect(screen.queryByRole("button", { name: "Hapus akun login" })).toBeNull();
  });

  it("SUPER_ADMIN: hapus akun login ada di zona berbahaya dan menyebut dampaknya", async () => {
    mockApi((c) => {
      if (c.url === `/employees/${ID}`) return { data: employee() };
      if (c.url === `/employees/${ID}/documents`) return { data: { items: [], total: 0 } };
      if (c.url === ACCOUNT) return { data: { exists: true, login: "a@contoh.id", is_active: true, system_role: "EMPLOYEE", failed_logins: 0, locked_until: null } };
      if (c.url === `${ACCOUNT}/sessions`) return { data: [] };
    });
    renderRoute(`/directory/${ID}`, { me: superAdmin() });
    const zone = await screen.findByText("Zona berbahaya");
    expect(zone.parentElement).toHaveTextContent("Hapus akun hanya bila karyawan tidak boleh masuk lagi");
    fireEvent.click(screen.getByRole("button", { name: "Hapus akun login" }));
    expect(await screen.findByText(/semua perangkatnya dikeluarkan/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hapus permanen" })).toBeDisabled(); // belum mengetik HAPUS
  });
});

describe("pengenalan wajah karyawan (HR)", () => {
  const FACE = `/face/enrollments/${ID}/status`;
  const mountWith = (status: Record<string, unknown>) =>
    mockApi((c) => {
      if (c.url === `/employees/${ID}`) return { data: employee() };
      if (c.url === `/employees/${ID}/documents`) return { data: { items: [], total: 0 } };
      if (c.url === ACCOUNT) return { data: { exists: false } };
      if (c.url === FACE) return { data: status };
    });

  it("belum terdaftar: tampil status belum terdaftar tanpa tombol atur ulang", async () => {
    mountWith({ enrolled: false, required: true });
    renderRoute(`/directory/${ID}`, { role: "HR" });
    expect(await screen.findByText("Belum terdaftar")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Atur ulang wajah" })).toBeNull();
  });

  it("terdaftar: atur ulang lewat konfirmasi memanggil DELETE /face/enrollments/{id}", async () => {
    const calls = mockApi((c) => {
      if (c.url === `/employees/${ID}`) return { data: employee() };
      if (c.url === `/employees/${ID}/documents`) return { data: { items: [], total: 0 } };
      if (c.url === ACCOUNT) return { data: { exists: false } };
      if (c.url === FACE && c.method === "get") return { data: { enrolled: true, required: true, enrolled_at: "2026-10-20T02:00:00Z" } };
      if (c.url === `/face/enrollments/${ID}` && c.method === "delete") return { data: { employee_id: ID, enrolled: false } };
    });
    renderRoute(`/directory/${ID}`, { role: "HR" });
    expect(await screen.findByText("Wajah terdaftar")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Atur ulang wajah" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ya, atur ulang" }));
    await waitFor(() => expect(calls.some((c) => c.method === "delete" && c.url === `/face/enrollments/${ID}`)).toBe(true));
  });
});

describe("halaman login: petunjuk penolakan", () => {
  const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });

  it("akun lapangan yang masuk lewat web: pesan penolakan dan petunjuk aplikasi HP", async () => {
    mockApi((c) => {
      if (c.url === "/auth/login")
        return apiError(403, "NOT_OFFICE_ACCOUNT", "Akun lapangan masuk lewat aplikasi HP Visiontech, bukan web.");
    });
    renderRoute("/login");
    type("Email", "lapangan@contoh.id");
    type("Password", "Rahasia123");
    await userEvent.setup().click(screen.getByRole("button", { name: "Masuk" }));
    const alert = await screen.findByTestId("login-error");
    expect(within(alert).getByText(/masuk lewat aplikasi HP Visiontech/)).toBeInTheDocument();
    expect(within(alert).getByText(/Unduh aplikasinya di bawah form ini/)).toBeInTheDocument();
  });

  it("batas perangkat: pesan jelas dan tautan petunjuk membuka dialog langkah-langkah", async () => {
    mockApi((c) => {
      if (c.url === "/auth/login")
        return apiError(403, "MAX_DEVICES_REACHED", "Akun ini sudah aktif di 4 perangkat.");
    });
    renderRoute("/login");
    type("Email", "penuh@contoh.id");
    type("Password", "Rahasia123");
    await userEvent.setup().click(screen.getByRole("button", { name: "Masuk" }));
    expect(await screen.findByText(/sudah aktif di 4 perangkat/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Lihat cara mengeluarkan perangkat lama" }));
    expect(await screen.findByRole("heading", { name: "Cara mengeluarkan perangkat lama" })).toBeInTheDocument();
    expect(screen.getByText(/Minta HR atau admin mengosongkan slot perangkat/)).toBeInTheDocument();
  });
});
