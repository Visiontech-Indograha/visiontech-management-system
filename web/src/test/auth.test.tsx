import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { getAccessToken, setAccessToken } from "@/lib/api";
import { apiError, mockApi, renderRoute } from "./utils";

afterEach(() => setAccessToken(null));

const TOKEN = { access_token: "tok", token_type: "bearer" };
const ME = {
  user_id: "u1",
  email: "budi@example.com",
  role: "field",
  permissions: ["view:users", "view:documents", "upload:documents"],
};

function type(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("login dan sesi API", () => {
  it("memvalidasi email dan password", async () => {
    mockApi(() => undefined);
    renderRoute("/login");
    fireEvent.click(screen.getByRole("button", { name: "Masuk" }));
    expect(await screen.findByText("Format email tidak valid.")).toBeInTheDocument();
    expect(screen.getByText("Password wajib diisi.")).toBeInTheDocument();
  });

  it("menampilkan galat login dari API", async () => {
    mockApi(() => apiError(401, "INVALID_CREDENTIALS", "Email atau password salah."));
    renderRoute("/login");
    type("Email", "budi@example.com");
    type("Password", "salah");
    fireEvent.click(screen.getByRole("button", { name: "Masuk" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email atau password salah.");
  });

  it("/auth/me dengan hanya empat field kontrak membuka beranda tanpa crash", async () => {
    const calls = mockApi((request) => {
      if (request.url === "/auth/login") return { data: TOKEN };
      if (request.url === "/auth/me") return { data: ME };
    });
    const { router } = renderRoute("/login");
    type("Email", ME.email);
    type("Password", "Rahasia123");
    fireEvent.click(screen.getByRole("button", { name: "Masuk" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(getAccessToken()).toBe("tok");
    expect(await screen.findByText("Selamat datang, budi@example.com.")).toBeInTheDocument();
    expect(await screen.findByText("Karyawan lapangan")).toBeInTheDocument();
    expect(calls.some((call) => call.url === "/auth/me")).toBe(true);
  });

  it("halaman login Admin memakai endpoint auth/login", async () => {
    const calls = mockApi((request) => {
      if (request.url === "/auth/login") return { data: TOKEN };
      if (request.url === "/auth/me") return { data: { ...ME, role: "ADMIN" } };
    });
    renderRoute("/admin-login");
    expect(screen.getByRole("heading", { name: "Masuk sebagai Admin" })).toBeInTheDocument();
    type("Email", "admin@example.com");
    type("Password", "Rahasia123");
    fireEvent.click(screen.getByRole("button", { name: "Masuk" }));
    await waitFor(() => expect(calls.some((call) => call.url === "/auth/login")).toBe(true));
  });
});

describe("ganti password sukarela", () => {
  it("validasi password baru tetap bekerja tanpa field must_change_password", async () => {
    mockApi(() => undefined);
    renderRoute("/change-password", { me: ME });
    type("Password saat ini", "Rahasia123");
    type("Password baru", "abc");
    type("Ulangi password baru", "abd");
    fireEvent.click(screen.getByRole("button", { name: "Ganti password" }));
    expect(await screen.findByText("Password minimal 8 karakter.")).toBeInTheDocument();
    expect(screen.getByText("Konfirmasi password tidak sama.")).toBeInTheDocument();
  });

  it("sesudah perubahan password, token baru dan /auth/me dipakai", async () => {
    mockApi((request) => {
      if (request.url === "/auth/change-password") return { data: { ...TOKEN, access_token: "baru" } };
      if (request.url === "/auth/me") return { data: ME };
    });
    const { router } = renderRoute("/change-password", { me: ME });
    type("Password saat ini", "Rahasia123");
    type("Password baru", "BaruLagi99");
    type("Ulangi password baru", "BaruLagi99");
    fireEvent.click(screen.getByRole("button", { name: "Ganti password" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(getAccessToken()).toBe("baru");
  });
});
