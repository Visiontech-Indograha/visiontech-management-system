import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { setAccessToken } from "@/lib/apiClient";
import { useSession } from "@/stores/sessionStore";
import { apiError, mockApi, renderRoute } from "./utils";

afterEach(() => setAccessToken(null));

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });

describe("penyiapan awal (/setup)", () => {
  const fill = (over: Partial<Record<string, string>> = {}) => {
    type("Kode penyiapan", over.token ?? "kode-rahasia");
    type("Nama lengkap", "Budi Admin");
    type("Email", "budi@visiontech.id");
    type("Sandi", over.password ?? "sandi-panjang-123");
    type("Ulangi sandi", over.confirm ?? over.password ?? "sandi-panjang-123");
  };

  it("form tampil bila perlu disiapkan dan aktif; sukses menuju halaman masuk", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/setup/status") return { data: { needs_setup: true, enabled: true } };
      if (c.url === "/setup/admin") return { data: { user_id: "u1", email: "budi@visiontech.id" } };
    });
    const { router } = renderRoute("/setup");
    await screen.findByLabelText("Kode penyiapan");
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Buat akun Super Admin" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(calls.find((c) => c.url === "/setup/admin")?.data).toEqual({
      setup_token: "kode-rahasia", full_name: "Budi Admin", email: "budi@visiontech.id", password: "sandi-panjang-123",
    });
  });

  it("memeriksa sandi 12 karakter dan konfirmasi", async () => {
    mockApi((c) => (c.url === "/setup/status" ? { data: { needs_setup: true, enabled: true } } : undefined));
    renderRoute("/setup");
    await screen.findByLabelText("Kode penyiapan");
    fill({ password: "pendek", confirm: "beda" });
    fireEvent.click(screen.getByRole("button", { name: "Buat akun Super Admin" }));
    expect(await screen.findByText("Sandi minimal 12 karakter.")).toBeInTheDocument();
    expect(screen.getByText("Konfirmasi sandi tidak sama.")).toBeInTheDocument();
  });

  it.each([
    [403, "SETUP_TOKEN_INVALID", /Kode penyiapan salah/],
    [409, "SETUP_LOCKED", /sudah disiapkan/],
    [409, "EMAIL_TAKEN", /sudah dipakai akun lain/],
  ])("galat %s %s tampil dengan pesan awam", async (status, code, pesan) => {
    mockApi((c) => {
      if (c.url === "/setup/status") return { data: { needs_setup: true, enabled: true } };
      if (c.url === "/setup/admin") return apiError(status, code, "pesan server");
    });
    renderRoute("/setup");
    await screen.findByLabelText("Kode penyiapan");
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Buat akun Super Admin" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(pesan);
  });

  it("422 dipetakan ke kolom lewat applyFieldErrors", async () => {
    mockApi((c) => {
      if (c.url === "/setup/status") return { data: { needs_setup: true, enabled: true } };
      if (c.url === "/setup/admin") return apiError(422, "VALIDATION_ERROR", "x", { fields: { email: "value is not a valid email address" } });
    });
    renderRoute("/setup");
    await screen.findByLabelText("Kode penyiapan");
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Buat akun Super Admin" }));
    expect(await screen.findByText("Format isian belum sesuai.")).toBeInTheDocument();
  });

  it("enabled=false: minta hubungi operator, tanpa form", async () => {
    mockApi((c) => (c.url === "/setup/status" ? { data: { needs_setup: true, enabled: false } } : undefined));
    renderRoute("/setup");
    expect(await screen.findByText("Hubungi operator untuk mengaktifkan penyiapan.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Kode penyiapan")).not.toBeInTheDocument();
  });

  it("sudah disiapkan: tidak ada form, ada tautan ke masuk", async () => {
    mockApi((c) => (c.url === "/setup/status" ? { data: { needs_setup: false, enabled: true } } : undefined));
    renderRoute("/setup");
    expect(await screen.findByText(/sudah disiapkan/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Kode penyiapan")).not.toBeInTheDocument();
  });

  it("halaman masuk menautkan ke /setup hanya bila needs_setup", async () => {
    mockApi((c) => (c.url === "/setup/status" ? { data: { needs_setup: true, enabled: true } } : undefined));
    const a = renderRoute("/login");
    expect(await screen.findByRole("link", { name: "Siapkan akun admin pertama" })).toBeInTheDocument();
    a.unmount();
    mockApi((c) => (c.url === "/setup/status" ? { data: { needs_setup: false, enabled: true } } : undefined));
    renderRoute("/login");
    await screen.findByRole("button", { name: "Masuk" });
    await waitFor(() => expect(screen.queryByRole("link", { name: "Siapkan akun admin pertama" })).not.toBeInTheDocument());
  });
});

describe("pemulihan sesi tanpa login", () => {
  it("refresh 401 tidak membuang query publik /setup/status yang sedang berjalan", async () => {
    mockApi((c) => {
      if (c.url === "/setup/status") return { data: { needs_setup: true, enabled: true } };
      if (c.url === "/auth/refresh") return apiError(401, "UNAUTHENTICATED", "Belum masuk.");
    });
    renderRoute("/setup");
    useSession.setState({ me: null, ready: false });
    await useSession.getState().initSession().catch(() => undefined);
    expect(await screen.findByLabelText("Kode penyiapan")).toBeInTheDocument();
  });
});

describe("wajib ganti sandi", () => {
  it("semua permintaan membawa header X-App-Capabilities: must-change-password", async () => {
    const calls = mockApi((c) => (c.url === "/setup/status" ? { data: { needs_setup: false, enabled: true } } : undefined));
    renderRoute("/login");
    await waitFor(() => expect(calls.length).toBeGreaterThan(0));
    expect((calls[0].headers as Record<string, string>)["X-App-Capabilities"]).toBe("must-change-password");
  });

  it("must_change_password=true: halaman lain dialihkan ke ganti sandi, ada tombol Keluar", async () => {
    mockApi(() => undefined);
    const { router } = renderRoute("/leaves", { me: { ...mockMe("field")!, must_change_password: true } });
    await waitFor(() => expect(router.state.location.pathname).toBe("/change-password"));
    expect(await screen.findByText(/masih sandi sementara/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Keluar" })).toBeInTheDocument();
  });

  it("403 MUST_CHANGE_PASSWORD dari server mengarahkan paksa ke ganti sandi", async () => {
    mockApi((c) => {
      if (c.url === "/leaves") return apiError(403, "MUST_CHANGE_PASSWORD", "Ganti sandi dulu.");
    });
    const { router } = renderRoute("/leaves", { me: { ...mockMe("field")!, must_change_password: false } });
    await waitFor(() => expect(router.state.location.pathname).toBe("/change-password"));
    expect(useSession.getState().me?.must_change_password).toBe(true);
  });

  it("Reset sandi karyawan meminta konfirmasi dulu", async () => {
    const ID = "00000000-0000-4000-8000-0000000000e1";
    const calls = mockApi((c) => {
      if (c.url === `/employees/${ID}`) return { data: { employee_id: ID, full_name: "Budi", is_active: true } };
      if (c.url === `/employees/${ID}/account` && c.method === "get")
        return { data: { exists: true, login: "a@contoh.id", is_active: true, system_role: "EMPLOYEE" } };
      if (c.url === `/employees/${ID}/account/reset-password`)
        return { data: { exists: true, login: "a@contoh.id", is_active: true, temporary_password: "Sementara123" } };
    });
    renderRoute(`/directory/${ID}`, { role: "HR" });
    fireEvent.click(await screen.findByRole("button", { name: "Reset sandi" }));
    expect(calls.some((c) => c.url.endsWith("/reset-password"))).toBe(false);
    fireEvent.click(await screen.findByRole("button", { name: "Ya, reset sandi" }));
    await screen.findByText("Sementara123");
    expect(calls.some((c) => c.url.endsWith("/reset-password"))).toBe(true);
  });
});

describe("peran utama di kartu akun", () => {
  const ID = "00000000-0000-4000-8000-0000000000e1";
  const setup = (role: string, accountRole: string, onRole?: () => ReturnType<Parameters<typeof mockApi>[0]>) =>
    mockApi((c) => {
      if (c.url === `/employees/${ID}`) return { data: { employee_id: ID, full_name: "Budi", is_active: true } };
      if (c.url === `/employees/${ID}/account` && c.method === "get")
        return { data: { exists: true, login: "a@contoh.id", is_active: true, system_role: accountRole } };
      if (c.url === `/employees/${ID}/account/role`) return onRole?.() ?? { data: { exists: true, system_role: "FINANCE" } };
    }) && renderRoute(`/directory/${ID}`, { me: { ...mockMe("HR")!, role } });

  it("Super Admin melihat tujuh peran dan wajib konfirmasi (sesi akan keluar)", async () => {
    const calls = mockApi((c) => {
      if (c.url === `/employees/${ID}`) return { data: { employee_id: ID, full_name: "Budi", is_active: true } };
      if (c.url === `/employees/${ID}/account` && c.method === "get")
        return { data: { exists: true, login: "a@contoh.id", is_active: true, system_role: "EMPLOYEE" } };
      if (c.url === `/employees/${ID}/account/role`) return { data: { exists: true, system_role: "FINANCE" } };
    });
    renderRoute(`/directory/${ID}`, { me: { ...mockMe("HR")!, role: "SUPER_ADMIN" } });
    const pilih = await screen.findByLabelText("Peran utama");
    expect(pilih.querySelectorAll("option")).toHaveLength(7);
    fireEvent.change(pilih, { target: { value: "FINANCE" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan peran" }));
    expect(await screen.findByText(/Semua sesi orang ini akan keluar/)).toBeInTheDocument();
    expect(calls.some((c) => c.url.endsWith("/role"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Ya, ubah peran" }));
    await waitFor(() => expect(calls.find((c) => c.url.endsWith("/role"))?.data).toEqual({ system_role: "FINANCE" }));
  });

  it("HR hanya melihat Ketua tim dan Karyawan lapangan", async () => {
    setup("ADMIN_HR_GA", "EMPLOYEE");
    const pilih = await screen.findByLabelText("Peran utama");
    expect(pilih.querySelectorAll("option")).toHaveLength(2);
  });

  it("galat 409 ROLE_SELF_CHANGE tampil dengan pesan awam", async () => {
    setup("SUPER_ADMIN", "EMPLOYEE", () => apiError(409, "ROLE_SELF_CHANGE", "x"));
    fireEvent.change(await screen.findByLabelText("Peran utama"), { target: { value: "HSE" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan peran" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ya, ubah peran" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("tidak bisa mengubah peran akun Anda sendiri");
  });
});

describe("batal pengajuan cuti sendiri", () => {
  const FUTURE = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
  const leave = (over: Record<string, unknown> = {}) => ({
    leave_id: "l1", employee_id: "e-lead", employee_name: "Uji Ketua", leave_type: "ANNUAL",
    start_date: FUTURE, end_date: FUTURE, total_days: 1, reason: "Keperluan keluarga", status: "PENDING",
    conflicts: [], create_at: "2026-10-27T10:00:00Z", ...over,
  });

  it("tombol Batalkan pengajuan: konfirmasi lalu POST /leaves/{id}/cancel", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/leaves" && c.method === "get") return { data: [leave()] };
      if (c.url === "/leaves/l1/cancel") return { data: leave({ status: "CANCELLED" }) };
    });
    renderRoute("/leaves", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Batalkan pengajuan Uji Ketua" }));
    expect(calls.some((c) => c.url.endsWith("/cancel"))).toBe(false);
    fireEvent.click(await screen.findByRole("button", { name: "Ya, batalkan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/leaves/l1/cancel")).toBe(true));
  });

  it("pengajuan orang lain atau yang sudah disetujui tidak punya tombol ini", async () => {
    mockApi((c) => {
      if (c.url === "/leaves" && c.method === "get")
        return { data: [leave({ leave_id: "l2", employee_id: "lain", employee_name: "Orang Lain" })] };
    });
    renderRoute("/leaves", { role: "field" });
    await screen.findByText("Orang Lain");
    expect(screen.queryByRole("button", { name: /Batalkan pengajuan/ })).not.toBeInTheDocument();
  });
});
