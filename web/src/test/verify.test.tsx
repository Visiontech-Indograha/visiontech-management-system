import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

/** Halaman PUBLIK verifikasi tanda tangan ber-QR (GET /verify/{token}) — dibuka orang luar tanpa login. */

const signature = (over: Record<string, unknown> = {}) => ({
  state: "VALID",
  serial_number: "SIG-2026-000123",
  signer_name: "Ade Pratama",
  signer_position: "Project Manager",
  signer_unit: "CCTV",
  signer_role: "ISSUER",
  document_number: "SK-202609-1a2b3c4d",
  document_title: "Instalasi CCTV gudang",
  signed_at: "2026-09-20T02:00:00Z",
  key_id: "doc-01a0-abcdef",
  algorithm: "Ed25519",
  document_sha256_hex: "ab".repeat(32),
  note: "Tanda tangan sah dan dokumen tidak berubah sejak ditandatangani.",
  ...over,
});

describe("verifikasi tanda tangan (publik)", () => {
  it("tanpa login: token (base64 berisi / + =) diteruskan utuh dan rincian sah ditampilkan", async () => {
    const token = "Ab/cd+EF==";
    const calls = mockApi((c) => (c.url === `/verify/${token}` ? { data: signature() } : undefined));
    renderRoute(`/verify/${token}`, { me: null });

    expect(await screen.findByText("Tanda tangan sah")).toBeInTheDocument();
    expect(calls.map((c) => c.url)).toEqual([`/verify/${token}`]);
    expect(screen.getByText("SK-202609-1a2b3c4d")).toBeInTheDocument();
    expect(screen.getByText("Ade Pratama")).toBeInTheDocument();
    expect(screen.getByText("Project Manager · CCTV")).toBeInTheDocument();
    expect(screen.getByText("SIG-2026-000123")).toBeInTheDocument();
    expect(screen.getByText("Ed25519 · doc-01a0-abcdef")).toBeInTheDocument();
  });

  it.each([
    ["DOCUMENT_CHANGED", "Dokumen tidak cocok", "Isi dokumen berbeda dengan yang ditandatangani. Jangan dipercaya."],
    ["REVOKED", "Tanda tangan dicabut", "Salah penandatangan"],
    ["KEY_EXPIRED", "Kunci penandatanganan dicabut", "Kunci penandatanganan telah dicabut; tanda tangan lama tetap tercatat."],
  ])("status %s tampil sebagai peringatan beserta alasannya", async (state, title, note) => {
    mockApi(() => ({ data: signature({ state, note }) }));
    renderRoute("/verify/tok", { me: null });
    expect(await screen.findByRole("status")).toHaveTextContent(title);
    expect(screen.getByRole("status")).toHaveTextContent(note);
    expect(screen.queryByText("Tanda tangan sah")).toBeNull();
  });

  it("QR tidak dikenal: tanpa rincian dokumen", async () => {
    mockApi(() => ({ data: { ...Object.fromEntries(Object.keys(signature()).map((k) => [k, null])), state: "UNKNOWN", note: "Kode QR tidak dikenal." } }));
    renderRoute("/verify/palsu", { me: null });
    expect(await screen.findByText("Kode QR tidak dikenal")).toBeInTheDocument();
    expect(screen.queryByText("Nomor dokumen")).toBeNull();
  });

  it("dibatasi (429) → pesan Indonesia dan tombol coba lagi memanggil ulang", async () => {
    let n = 0;
    mockApi(() => (++n === 1 ? apiError(429, "TOO_MANY_REQUESTS", "Terlalu banyak permintaan. Coba lagi sebentar.") : { data: signature() }));
    renderRoute("/verify/tok", { me: null });
    expect(await screen.findByRole("alert")).toHaveTextContent("Terlalu banyak permintaan. Coba lagi sebentar.");
    fireEvent.click(screen.getByRole("button", { name: "Coba lagi" }));
    await waitFor(() => expect(screen.getByText("Tanda tangan sah")).toBeInTheDocument());
    expect(n).toBe(2);
  });

  it("tautan tanpa token", async () => {
    mockApi(() => undefined);
    renderRoute("/verify/", { me: null });
    expect(await screen.findByText("Tautan verifikasi tidak lengkap.")).toBeInTheDocument();
  });
});
