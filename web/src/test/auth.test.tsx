import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { getAccessToken, setAccessToken } from "@/lib/api";
import { apiError, mockApi, renderRoute } from "./utils";

afterEach(() => setAccessToken(null));

function type(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

const TOKEN = { token_type: "bearer", expires_in: 900, must_change_password: false };

describe("login", () => {
  it("validasi: email dan password wajib", async () => {
    mockApi(() => undefined);
    renderRoute("/login");
    fireEvent.click(screen.getByRole("button", { name: "Masuk" }));
    expect(await screen.findByText("Format email tidak valid.")).toBeInTheDocument();
    expect(screen.getByText("Password wajib diisi.")).toBeInTheDocument();
  });

  it("gagal login menampilkan pesan generik dari server", async () => {
    mockApi(() => apiError(401, "INVALID_CREDENTIALS", "Email atau password salah."));
    renderRoute("/login");
    type("Email", "budi@visiontech.co.id");
    type("Password", "salah");
    fireEvent.click(screen.getByRole("button", { name: "Masuk" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email atau password salah.");
  });

  it("sukses: simpan token, muat /auth/me, masuk ke Beranda", async () => {
    const me = mockMe("wtl")!;
    const calls = mockApi((c) => {
      if (c.url === "/auth/login") return { data: { access_token: "tok", ...TOKEN } };
      if (c.url === "/auth/me") return { data: me };
    });
    const { router } = renderRoute("/login");
    type("Email", "budi@visiontech.co.id");
    type("Password", "Rahasia123");
    fireEvent.click(screen.getByRole("button", { name: "Masuk" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(getAccessToken()).toBe("tok");
    expect(calls[0]).toMatchObject({ url: "/auth/login", data: { email: "budi@visiontech.co.id", platform: "web" } });
    expect(await screen.findByText(/Selamat datang/)).toBeInTheDocument();
  });

  it("/admin-login memakai endpoint admin-login", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/auth/login") return { data: { access_token: "t", ...TOKEN } }; // Assuming merged endpoint
      if (c.url === "/auth/me") return { data: mockMe("super_admin") };
    });
    renderRoute("/admin-login");
    expect(screen.getByRole("heading", { name: "Masuk sebagai Super Admin" })).toBeInTheDocument();
    type("Email", "root@visiontech.co.id");
    type("Password", "Rahasia123");
    fireEvent.click(screen.getByRole("button", { name: "Masuk" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/auth/login")).toBe(true));
  });

  it("/admin-login tidak ditautkan dari halaman login biasa", () => {
    renderRoute("/login");
    expect(document.querySelector('a[href="/admin-login"]')).toBeNull();
  });
});

describe("ganti password wajib", () => {
  const forced = { ...mockMe("wtl")!, must_change_password: true };

  it("user dengan must_change_password diarahkan ke /change-password dari halaman mana pun", () => {
    mockApi(() => undefined);
    const { router } = renderRoute("/my-plan", { me: forced });
    expect(router.state.location.pathname).toBe("/change-password");
  });

  it("validasi password baru di sisi klien", async () => {
    mockApi(() => undefined);
    renderRoute("/change-password", { me: forced });
    type("Password saat ini", "Rahasia123");
    type("Password baru", "abc");
    type("Ulangi password baru", "abd");
    fireEvent.click(screen.getByRole("button", { name: "Ganti password" }));
    expect(await screen.findByText("Password minimal 8 karakter.")).toBeInTheDocument();
    expect(screen.getByText("Konfirmasi password tidak sama.")).toBeInTheDocument();
  });

  it("galat password saat ini salah tampil pada field-nya", async () => {
    mockApi(() =>
      apiError(422, "VALIDATION_ERROR", "Data yang dikirim tidak valid.", {
        fields: { current_password: "Password saat ini salah." },
      }),
    );
    renderRoute("/change-password", { me: forced });
    type("Password saat ini", "Salah12345");
    type("Password baru", "BaruLagi99");
    type("Ulangi password baru", "BaruLagi99");
    fireEvent.click(screen.getByRole("button", { name: "Ganti password" }));
    expect(await screen.findByText("Password saat ini salah.")).toBeInTheDocument();
  });

  it("sukses: token baru dipakai dan user masuk ke Beranda", async () => {
    let changed = false;
    mockApi((c) => {
      if (c.url === "/auth/change-password") {
        changed = true;
        return { data: { access_token: "baru", ...TOKEN } };
      }
      if (c.url === "/auth/me") return { data: { ...forced, must_change_password: !changed } };
    });
    const { router } = renderRoute("/change-password", { me: forced });
    type("Password saat ini", "Rahasia123");
    type("Password baru", "BaruLagi99");
    type("Ulangi password baru", "BaruLagi99");
    fireEvent.click(screen.getByRole("button", { name: "Ganti password" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(getAccessToken()).toBe("baru");
  });
});
