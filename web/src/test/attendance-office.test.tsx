import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockMe } from "@/app/mockSession";
import type { Me } from "@/lib/types";
import { mockApi, renderRoute } from "./utils";

/** R-33: absen kantor lewat web (Finance meninjau; ajukan ulang sekali; pulang hanya bila valid). */
const OFFICE = { lat: -6.2253, lng: 106.8024 };
const FAR = { lat: -6.24, lng: 106.8024 }; // ±1,6 km
const site = { id: "s-office", name: "Kantor Pusat", location: OFFICE, radius_m: 150, unit_id: null, can_manage: false };

const officeMe = (mode: "OFFICE" | "FIELD" = "OFFICE"): Me =>
  ({ ...mockMe("FINANCE")!, employee_id: "e-fin", attendance_mode: mode }) as Me;

const att = (over: Record<string, unknown> = {}) => ({
  id: "a-fin",
  employee_id: "e-fin",
  work_date: "2026-10-02",
  site_id: site.id,
  site_label: site.name,
  check_in_at: "2026-10-02T01:00:00Z",
  check_out_at: null,
  distance_m: 12,
  is_late: false,
  is_early_leave: false,
  status: "AUTO_VALID",
  explanation: null,
  reviewed_at: null,
  employee_name: "Agus",
  selfie_file_id: null,
  can_review: false,
  ...over,
});

function stubLocation(at: { lat: number; lng: number }) {
  vi.stubGlobal("navigator", {
    ...navigator,
    geolocation: {
      getCurrentPosition: (ok: PositionCallback) =>
        ok({ coords: { latitude: at.lat, longitude: at.lng, accuracy: 20 } } as GeolocationPosition),
    },
  });
}

const setup = (items: unknown[], extra?: (url: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "");
    if (hit) return hit;
    if (c.url === "/attendance") return { data: { items, total: items.length, page: 1, size: 50, today: "2026-10-02" } };
    if (c.url === "/offices") return { data: [site] };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
  });

const card = async () => screen.findByRole("region", { name: "Absen hari ini" });

describe("Absen kantor lewat web (R-33)", () => {
  beforeEach(() => {
    stubLocation(OFFICE);
    // Jam tetap 18.30 WIB — aturan jam absen (06.45 masuk, 19.00 batas pulang) tidak tergantung jam CI.
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-10-02T11:30:00Z") });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("pekerja lapangan diarahkan ke aplikasi HP", async () => {
    setup([]);
    renderRoute("/attendance", { me: officeMe("FIELD") });
    expect(await within(await card()).findByText(/Absen masuk dan pulang dilakukan lewat aplikasi HP/)).toBeInTheDocument();
    expect(within(await card()).queryByRole("button", { name: "Absen masuk" })).not.toBeInTheDocument();
  });

  it("di dalam radius: swafoto selalu diminta dulu (docs/35 §5), tanpa penjelasan", async () => {
    const calls = setup([], (url) => (url === "/attendance/check-in" ? { data: att() } : undefined));
    renderRoute("/attendance", { me: officeMe() });
    fireEvent.click(await within(await card()).findByRole("button", { name: "Absen masuk" }));
    expect(await screen.findByText("Ambil swafoto wajah Anda untuk absen masuk.")).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/attendance/check-in")).toBe(false); // belum terkirim sebelum swafoto
  });

  it("di luar radius: penjelasan wajib diisi sebelum dikirim", async () => {
    stubLocation(FAR);
    const calls = setup([]);
    renderRoute("/attendance", { me: officeMe() });
    const region = await card();
    fireEvent.click(await within(region).findByRole("button", { name: "Absen masuk" }));
    expect(await within(region).findByRole("alert")).toHaveTextContent(/dari Kantor Pusat \(radius 150 m\)\. Isi penjelasan/);
    expect(within(region).getByLabelText("Penjelasan (wajib)")).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/attendance/check-in")).toBe(false);
  });

  it("ditolak sekali: boleh ajukan ulang dengan penjelasan wajib", async () => {
    const calls = setup([att({ status: "REJECTED", review_note: "Foto buram" })], (url) =>
      url === "/attendance/check-in" ? { data: att({ id: "a-2" }) } : undefined,
    );
    renderRoute("/attendance", { me: officeMe() });
    const region = await card();
    expect(await within(region).findByText(/Absensi ditolak: Foto buram\. Anda dapat mengajukan absen ulang satu/)).toBeInTheDocument();
    const resubmit = within(region).getByRole("button", { name: "Ajukan absen ulang" });
    fireEvent.click(resubmit);
    expect(await within(region).findByRole("alert")).toHaveTextContent("Isi penjelasan untuk mengajukan ulang");
    fireEvent.change(within(region).getByLabelText("Penjelasan (wajib)"), { target: { value: "Foto ulang lebih jelas" } });
    fireEvent.click(resubmit);
    // Penjelasan lengkap → lanjut ke swafoto wajib (docs/35 §5); kiriman ke server terjadi setelah foto diambil.
    expect(await screen.findByText(/Ambil swafoto/)).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/attendance/check-in")).toBe(false);
  });

  it("ditolak dua kali: hari itu terkunci", async () => {
    setup([att({ id: "r1", status: "REJECTED" }), att({ id: "r2", status: "REJECTED" })]);
    renderRoute("/attendance", { me: officeMe() });
    const region = await card();
    expect(await within(region).findByText(/ditolak 2 kali dan tidak dapat diajukan lagi/)).toBeInTheDocument();
    expect(within(region).queryByRole("button", { name: /Absen masuk|Ajukan absen ulang/ })).not.toBeInTheDocument();
  });

  it("menunggu pemeriksaan: absen pulang belum bisa", async () => {
    setup([att({ status: "NEEDS_REVIEW", distance_m: 1600 })]);
    renderRoute("/attendance", { me: officeMe() });
    const region = await card();
    expect(await within(region).findByText(/Absen pulang bisa dilakukan setelah absen masuk disetujui/)).toBeInTheDocument();
    expect(within(region).queryByRole("button", { name: "Absen pulang" })).not.toBeInTheDocument();
  });

  it("absen masuk valid: absen pulang kanal WEB", async () => {
    const calls = setup([att()], (url) =>
      url === "/attendance/check-out" ? { data: att({ check_out_at: "2026-10-02T10:00:00Z" }) } : undefined,
    );
    renderRoute("/attendance", { me: officeMe() });
    fireEvent.click(await within(await card()).findByRole("button", { name: "Absen pulang" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/attendance/check-out")).toBe(true));
    expect(calls.find((c) => c.url === "/attendance/check-out")!.data).toMatchObject({ channel: "WEB", location: OFFICE });
  });

  it("absen masuk baru bisa mulai 06:45 WIB", async () => {
    vi.setSystemTime(new Date("2026-10-01T23:44:00Z")); // 06:44 WIB
    const calls = setup([]);
    renderRoute("/attendance", { me: officeMe() });
    const region = await card();
    fireEvent.click(await within(region).findByRole("button", { name: "Absen masuk" }));
    expect(await within(region).findByRole("alert")).toHaveTextContent("dimulai pukul 06:45 WIB");
    expect(calls.some((c) => c.url === "/attendance/check-in")).toBe(false);
  });

  it("laporan harian belum diisi: peringatan sebelum absen pulang, tetap boleh lanjut", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/attendance")
        return { data: { items: [att()], total: 1, page: 1, size: 50, today: "2026-10-02", report_pending_count: 2 } };
      if (c.url === "/attendance/check-out") return { data: att({ check_out_at: "2026-10-02T10:00:00Z" }) };
      if (c.url === "/offices") return { data: [site] };
      if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    });
    renderRoute("/attendance", { me: officeMe() });
    fireEvent.click(await within(await card()).findByRole("button", { name: "Absen pulang" }));
    expect(await screen.findByText(/2 tugas hari ini yang progresnya belum diperbarui/)).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/attendance/check-out")).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Tetap absen pulang" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/attendance/check-out")).toBe(true));
  });

  it("wajah V2: tidak ada langkah verifikasi wajah terpisah (server mencocokkan swafoto absen)", async () => {
    const calls = setup([], (url) => (url === "/face/status" ? { data: { enrolled: true, required: false } } : undefined));
    renderRoute("/attendance", { me: officeMe() });
    fireEvent.click(await within(await card()).findByRole("button", { name: "Absen masuk" }));
    expect(await screen.findByText("Ambil swafoto wajah Anda untuk absen masuk.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mulai Verifikasi Wajah" })).toBeNull();
    expect(calls.some((c) => c.url.startsWith("/face/probe"))).toBe(false);
  });
});
