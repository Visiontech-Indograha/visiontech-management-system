import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute, apiError } from "./utils";

/** M1 / P1-7: Akun & keamanan — ganti password bisa ditemukan, daftar perangkat, keluarkan perangkat. */

const sessions = [
  { id: "s1", device_label: "Web Login", ip_address: "10.0.0.2", user_agent: "Mozilla/5.0 (Windows NT 10.0) Chrome/140.0",
    issued_at: "2026-09-27T01:00:00Z", last_used_at: "2026-09-27T03:00:00Z", current: true },
  { id: "s2", device_label: "Android", ip_address: "10.0.0.9", user_agent: "Dart/3.9 (dart:io) Android",
    issued_at: "2026-09-26T01:00:00Z", last_used_at: null, current: false },
];

describe("Akun & keamanan", () => {
  it("tautan di menu, perangkat ini ditandai, perangkat lain bisa dikeluarkan satu per satu", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/auth/sessions") return { data: sessions };
      if (c.url === "/auth/sessions/s2/revoke") return { data: { message: "ok" } };
    });
    renderRoute("/account", { role: "PM" });

    expect(screen.getByRole("link", { name: "Akun & keamanan" })).toHaveAttribute("href", "/account");
    expect(await screen.findByRole("link", { name: "Ganti password" })).toHaveAttribute("href", "/change-password");
    const list = await screen.findByRole("region", { name: "Perangkat yang masuk" });
    expect(await within(list).findByText("Perangkat ini")).toBeInTheDocument();
    expect(within(list).getByText(/Chrome · Windows/)).toBeInTheDocument();
    expect(within(list).getByText(/Aplikasi Visiontech · Android/)).toBeInTheDocument();

    fireEvent.click(within(list).getByRole("button", { name: "Keluarkan Aplikasi Visiontech · Android" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/auth/sessions/s2/revoke")).toBe(true));
    expect(within(list).queryByRole("button", { name: /Keluarkan Chrome/ })).toBeNull(); // perangkat ini tidak bisa
  });

  it("keluarkan semua perangkat lain", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/auth/sessions") return { data: sessions };
      if (c.url === "/auth/sessions/revoke-others") return { data: { revoked: 1, message: "ok" } };
    });
    renderRoute("/account", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Keluarkan perangkat lain" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/auth/sessions/revoke-others")).toBe(true));
  });

  it("hanya satu perangkat: tombol keluarkan perangkat lain tidak tampil", async () => {
    mockApi((c) => (c.url === "/auth/sessions" ? { data: [sessions[0]] } : undefined));
    renderRoute("/account", { role: "field" });
    await screen.findByText("Perangkat ini");
    expect(screen.queryByRole("button", { name: "Keluarkan perangkat lain" })).toBeNull();
  });

  describe("Biometrik wajah", () => {
    const faceStatus = (over: Record<string, unknown> = {}) => ({
      employee_linked: true, consent: null, consent_policy_version: null, enrolled: false, enrollment_version: null,
      model_name: null, model_version: null, liveness_required: true, template_ttl_days: 7,
      policy: { version: "2026-10-05", text: "Saya menyetujui pemakaian data wajah HANYA untuk absensi." }, ...over,
    });
    const setup = (status: Record<string, unknown>) =>
      mockApi((c) => {
        if (c.url === "/auth/sessions") return { data: [] };
        if (c.url === "/face/status") return { data: status };
        if (c.url === "/face/consent") return { data: { message: "ok" } };
      });

    it("persetujuan memakai versi dari server dan butuh centang", async () => {
      const calls = setup(faceStatus());
      renderRoute("/account", { role: "field" });
      expect(await screen.findByText(/HANYA untuk absensi/)).toBeInTheDocument();
      const button = screen.getByRole("button", { name: "Beri Persetujuan Biometrik" });
      expect(button).toBeDisabled(); // belum dicentang
      fireEvent.click(screen.getByRole("checkbox"));
      fireEvent.click(button);
      await waitFor(() => expect(calls.some((c) => c.url === "/face/consent")).toBe(true));
      expect(calls.find((c) => c.url === "/face/consent")!.data).toEqual({ state: "GRANTED", policy_version: "2026-10-05" });
    });

    it("pendaftaran wajah di web lewat kamera langsung, bukan pilih berkas", async () => {
      setup(faceStatus({ consent: "GRANTED", consent_policy_version: "2026-10-05" }));
      renderRoute("/account", { role: "field" });
      const info = await screen.findByTestId("face-enroll-info");
      expect(within(info).getByTestId("face-capture")).toBeInTheDocument();
      expect(within(info).getByRole("button", { name: "Mulai Pendaftaran Wajah" })).toBeInTheDocument();
      expect(document.querySelector('input[type="file"]')).toBeNull(); // foto orang lain tak bisa didaftarkan
    });

    it("sudah terdaftar: menampilkan masa berlaku template dan tombol daftar ulang", async () => {
      setup(faceStatus({ consent: "GRANTED", enrolled: true, model_name: "w600k_mbf", enrollment_version: "3-1" }));
      renderRoute("/account", { role: "field" });
      const info = await screen.findByTestId("face-enroll-info");
      expect(within(info).getByText("w600k_mbf")).toBeInTheDocument();
      expect(within(info).getByText("7 hari")).toBeInTheDocument();
      expect(within(info).getByRole("button", { name: "Daftar Ulang Wajah" })).toBeInTheDocument();
    });

    it("menarik persetujuan mengirim WITHDRAWN dengan versi kebijakan server", async () => {
      const calls = setup(faceStatus({ consent: "GRANTED", enrolled: true, model_name: "w600k_mbf" }));
      renderRoute("/account", { role: "field" });
      fireEvent.click(await screen.findByRole("button", { name: "Tarik Persetujuan" }));
      await waitFor(() => expect(calls.some((c) => c.url === "/face/consent")).toBe(true));
      expect(calls.find((c) => c.url === "/face/consent")!.data).toEqual({ state: "WITHDRAWN", policy_version: "2026-10-05" });
    });
  });
});

describe("Wajib daftar wajah setelah login", () => {
  const status = (over: Record<string, unknown> = {}) => ({
    employee_linked: true, consent: null, consent_policy_version: null, enrolled: false, enrollment_version: null,
    model_name: null, model_version: null, liveness_required: true, enrollment_required: true, template_ttl_days: 7,
    policy: { version: "2026-10-05", text: "Saya menyetujui pemakaian data wajah HANYA untuk absensi." }, ...over,
  });

  it("belum terdaftar: menu lain tertutup, muncul persetujuan lebih dulu", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/face/status") return { data: status() };
      if (c.url === "/face/consent") return { data: { message: "ok" } };
    });
    renderRoute("/work-plans", { role: "field" });
    expect(await screen.findByTestId("face-gate")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Akun & keamanan" })).toBeNull(); // menu tidak tampil
    const agree = screen.getByRole("button", { name: "Setuju dan Lanjut" });
    expect(agree).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(agree);
    await waitFor(() => expect(calls.find((c) => c.url === "/face/consent")?.data).toEqual({
      state: "GRANTED", policy_version: "2026-10-05",
    }));
  });

  it("sudah setuju: langsung kamera pendaftaran", async () => {
    mockApi((c) => (c.url === "/face/status" ? { data: status({ consent: "GRANTED" }) } : undefined));
    renderRoute("/work-plans", { role: "field" });
    const gate = await screen.findByTestId("face-gate");
    expect(within(gate).getByTestId("face-capture")).toBeInTheDocument();
  });

  it("tidak diwajibkan server (atau sudah terdaftar): halaman terbuka normal", async () => {
    mockApi((c) => {
      if (c.url === "/auth/sessions") return { data: [] };
      if (c.url === "/face/status") return { data: status({ enrollment_required: false, consent: "GRANTED", enrolled: true }) };
    });
    renderRoute("/account", { role: "field" });
    expect(await screen.findByRole("link", { name: "Ganti password" })).toBeInTheDocument();
    expect(screen.queryByTestId("face-gate")).toBeNull();
  });

  it("ganti password tetap bisa dibuka walau wajib daftar wajah (tidak ikut terkunci)", async () => {
    mockApi((c) => (c.url === "/face/status" ? { data: status() } : undefined));
    renderRoute("/change-password", { role: "field" });
    await waitFor(() => expect(screen.queryByTestId("face-gate")).toBeNull());
    expect(await screen.findByRole("heading", { name: /ganti password/i })).toBeInTheDocument();
  });

  it("akun tanpa karyawan (admin murni): tidak pernah dikunci gerbang walau server mewajibkan", async () => {
    mockApi((c) => {
      if (c.url === "/auth/sessions") return { data: [] };
      if (c.url === "/face/status") return { data: status({ employee_linked: false, enrollment_required: false }) };
    });
    renderRoute("/account", { role: "ADMIN" });
    expect(await screen.findByRole("link", { name: "Ganti password" })).toBeInTheDocument();
    expect(screen.queryByTestId("face-gate")).toBeNull();
  });
});

describe("Tata letak halaman Akun & keamanan", () => {
  it("responsif: dua kolom di desktop (lg), urutan ponsel Akun → Biometrik → Perangkat", async () => {
    mockApi((c) => {
      if (c.url === "/auth/sessions") return { data: [] };
      if (c.url === "/face/status") {
        return { data: { employee_linked: true, consent: "GRANTED", consent_policy_version: "v1", enrolled: false,
          liveness_required: true, template_ttl_days: 7, policy: { version: "v1", text: "t" } } };
      }
    });
    renderRoute("/account", { role: "field" });
    const akun = await screen.findByRole("region", { name: "Akun" });
    const wajah = await screen.findByRole("region", { name: "Biometrik Wajah" });
    const perangkat = await screen.findByRole("region", { name: "Perangkat yang masuk" });

    const order = [akun, wajah, perangkat].map((e) => e.compareDocumentPosition(perangkat));
    expect(order[0]! & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();   // Akun mendahului Perangkat
    expect(akun.compareDocumentPosition(wajah) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(wajah.compareDocumentPosition(perangkat) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    const grid = akun.parentElement!;
    expect(grid.className).toContain("lg:grid-cols-2");
    expect(grid.className).toContain("grid");
    for (const card of [akun, wajah]) expect(card.className).not.toContain("max-w-xl"); // tak lagi dibatasi sempit
  });
});

/**
 * Foto profil memakai presigned URL dari `/files/{id}/url` — BUKAN `<img src="/api/v1/files/{id}">`,
 * karena browser tidak menyertakan header Authorization pada permintaan gambar sehingga API
 * selalu menjawab 404. Kunci kueri disamakan dengan FilePreview agar tidak meminta URL dua kali.
 */
describe("Foto profil di Akun & keamanan", () => {
  const ME_WITH_PHOTO = {
    user_id: "u-1", email: "ramadani@visiontech.id", role: "PM",
    permissions: ["view:users", "view:documents"], employee_id: "e-1",
    photo_file_id: "f-photo",
  };
  const FACE_OK = { data: { employee_linked: true, consent: "GRANTED", consent_policy_version: "v1",
    enrolled: true, liveness_required: true, template_ttl_days: 7, policy: { version: "v1", text: "t" } } };

  it("mengambil URL bertanda tangan lewat API lalu menampilkan gambar", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/auth/me") return { data: ME_WITH_PHOTO };
      if (c.url === "/auth/sessions") return { data: [] };
      if (c.url === "/face/status") return FACE_OK;
      if (c.url === "/files/f-photo/url?variant=view") {
        return { data: { url: "http://minio.test/vms-files/f-photo_view.webp", mime_type: "image/webp" } };
      }
    });
    renderRoute("/account", { me: ME_WITH_PHOTO as never });

    const akun = await screen.findByRole("region", { name: "Akun" });
    const img = await within(akun).findByRole("img");
    expect(img).toHaveAttribute("src", "http://minio.test/vms-files/f-photo_view.webp");
    expect(calls.some((c) => c.url === "/files/f-photo/url?variant=view")).toBe(true);
  });

  it("tanpa photo_file_id: tidak ada gambar, tidak ada permintaan URL", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/auth/me") return { data: { ...ME_WITH_PHOTO, photo_file_id: null } };
      if (c.url === "/auth/sessions") return { data: [] };
      if (c.url === "/face/status") return FACE_OK;
    });
    renderRoute("/account", { me: { ...ME_WITH_PHOTO, photo_file_id: null } as never });

    const akun = await screen.findByRole("region", { name: "Akun" });
    expect(within(akun).queryByRole("img")).toBeNull();
    expect(calls.some((c) => String(c.url).includes("/url"))).toBe(false);
  });

  it("URL gagal diambil: kartu akun tetap tampil tanpa gambar", async () => {
    mockApi((c) => {
      if (c.url === "/auth/me") return { data: ME_WITH_PHOTO };
      if (c.url === "/auth/sessions") return { data: [] };
      if (c.url === "/face/status") return FACE_OK;
      if (c.url === "/files/f-photo/url?variant=view") return apiError(404, "NOT_FOUND", "Berkas tidak ditemukan.");
    });
    renderRoute("/account", { me: ME_WITH_PHOTO as never });

    const akun = await screen.findByRole("region", { name: "Akun" });
    expect(within(akun).getByText("ramadani@visiontech.id")).toBeInTheDocument();
    expect(within(akun).queryByRole("img")).toBeNull();
  });
});
