import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { UserOut } from "@/lib/types";
import { apiError, mockApi, renderRoute } from "./utils";

const user = (over: Partial<UserOut> = {}): UserOut => ({
  id: "11111111-1111-1111-1111-111111111111",
  username: "budi.s",
  full_name: "Budi Santoso",
  role: "user",
  user_type: "WTL",
  is_active: true,
  must_change_password: false,
  last_login_at: null,
  deactivated_at: null,
  deactivation_reason: null,
  created_at: "2026-09-01T00:00:00Z",
  employment_type: "CONTRACT",
  ...over,
});

const page = (items: UserOut[]) => ({ items, total: items.length, page: 1, page_size: 25 });

describe("halaman Pengguna", () => {
  it("hanya Super Admin yang dapat membukanya", () => {
    mockApi(() => undefined);
    const { router } = renderRoute("/users", { role: "admin" });
    expect(router.state.location.pathname).toBe("/forbidden");
  });

  it("menampilkan daftar dengan badge status", async () => {
    mockApi((c) => {
      if (c.url === "/users")
        return {
          data: page([user(), user({ id: "2", username: "citra", full_name: "Citra Dewi", is_active: false })]),
        };
    });
    renderRoute("/users", { role: "super_admin" });
    expect(await screen.findByText("Budi Santoso")).toBeInTheDocument();
    expect(screen.getByText("Aktif", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("Nonaktif", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aktifkan" })).toBeInTheDocument();
  });

  it("keadaan kosong", async () => {
    mockApi((c) => (c.url === "/users" ? { data: page([]) } : undefined));
    renderRoute("/users", { role: "super_admin" });
    expect(await screen.findByText("Tidak ada pengguna yang cocok.")).toBeInTheDocument();
  });

  it("galat memuat daftar", async () => {
    mockApi(() => apiError(500, "INTERNAL_ERROR", "x"));
    renderRoute("/users", { role: "super_admin" });
    expect(await screen.findByText(/tidak dapat dimuat/)).toBeInTheDocument();
  });

  it("membuat user: password sementara ditampilkan sekali", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/users" && c.method === "get") return { data: page([]) };
      if (c.url === "/users" && c.method === "post")
        return { status: 201, data: { ...user({ username: "baru.user" }), temporary_password: "Ab3dEf7hJk9m" } };
    });
    renderRoute("/users", { role: "super_admin" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah user" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah user" });
    fireEvent.change(within(dialog).getByLabelText("Username"), { target: { value: "baru.user" } });
    fireEvent.change(within(dialog).getByLabelText("Nama lengkap"), { target: { value: "User Baru" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Buat user" }));

    expect(await screen.findByTestId("temp-password")).toHaveTextContent("Ab3dEf7hJk9m");
    const post = calls.find((c) => c.method === "post" && c.url === "/users")!;
    expect(post.data).toMatchObject({
      username: "baru.user",
      role: "user",
      user_type: "WTL",
      employment_type: "CONTRACT",
    });

    fireEvent.click(screen.getByRole("button", { name: "Selesai" }));
    await waitFor(() => expect(screen.queryByTestId("temp-password")).toBeNull());
  });

  it("galat validasi server tampil pada field", async () => {
    mockApi((c) => {
      if (c.method === "get") return { data: page([]) };
      return apiError(422, "VALIDATION_ERROR", "x", { fields: { username: "Username sudah dipakai." } });
    });
    renderRoute("/users", { role: "super_admin" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah user" }));
    fireEvent.click(screen.getByRole("button", { name: "Buat user" }));
    expect(await screen.findByText("Username sudah dipakai.")).toBeInTheDocument();
  });

  it("nonaktifkan: alasan dikirim dan peringatan item terbuka tampil", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/users" && c.method === "get") return { data: page([user()]) };
      if (c.url?.endsWith("/open-items")) return { data: { vehicle_loans: [{ id: "v" }], issuances: [] } };
      if (c.url?.endsWith("/deactivate")) return { data: user({ is_active: false }) };
    });
    renderRoute("/users", { role: "super_admin" });
    fireEvent.click(await screen.findByRole("button", { name: "Nonaktifkan" }));
    const dialog = await screen.findByRole("dialog", { name: /Nonaktifkan Budi Santoso/ });
    expect(await within(dialog).findByRole("status")).toHaveTextContent("1 kendaraan");
    fireEvent.change(within(dialog).getByLabelText("Alasan"), { target: { value: "Resign" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Nonaktifkan" }));
    await waitFor(() => expect(calls.some((c) => c.url?.endsWith("/deactivate"))).toBe(true));
    expect(calls.find((c) => c.url?.endsWith("/deactivate"))!.data).toMatchObject({ reason: "Resign" });
  });

  it("reset password menampilkan password sementara", async () => {
    mockApi((c) => {
      if (c.url === "/users") return { data: page([user()]) };
      if (c.url?.endsWith("/reset-password")) return { data: { temporary_password: "Zx9yWv8uTs7r" } };
    });
    renderRoute("/users", { role: "super_admin" });
    fireEvent.click(await screen.findByRole("button", { name: "Reset password" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Reset password" }));
    expect(await screen.findByTestId("temp-password")).toHaveTextContent("Zx9yWv8uTs7r");
  });
});

describe("halaman Audit log", () => {
  it("menampilkan catatan dalam WIB dan detail sebelum/sesudah", async () => {
    mockApi((c) => {
      if (c.url === "/audit-events")
        return {
          data: {
            items: [
              {
                id: "a1",
                actor_label: "admin@visiontech.co.id",
                action: "user.deactivate",
                entity_type: "user",
                entity_id: "11111111-0000-0000-0000-000000000000",
                detail: "Deactivated user",
                changes: { "is_active": false },
                occurred_at: "2026-09-21T00:42:00Z",
              },
            ],
            total: 1,
            page: 1,
            size: 25,
          },
        };
    });
    renderRoute("/audit-logs", { role: "super_admin" });
    expect(await screen.findByText("user.deactivate", { selector: "td" })).toBeInTheDocument();
    expect(screen.getByText("21 Sep 2026 07.42 WIB")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Lihat" }));
    expect(screen.getByText(/"is_active": false/)).toBeInTheDocument();
  });

  it("role selain Super Admin ditolak", () => {
    mockApi(() => undefined);
    const { router } = renderRoute("/audit-logs", { role: "finance" });
    expect(router.state.location.pathname).toBe("/forbidden");
  });
});
