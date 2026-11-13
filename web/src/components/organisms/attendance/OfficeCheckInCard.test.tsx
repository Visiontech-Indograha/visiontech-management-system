import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockMe } from "@/app/mockSession";
import type { Me } from "@/lib/types";
import { mockApi, renderRoute } from "@/test/utils";

/** E5-4: pulang di luar zona meminta penjelasan lalu foto bukti sebelum kirim (sama dengan HP). */
const OFFICE = { lat: -6.2253, lng: 106.8024 };
const FAR = { lat: -6.24, lng: 106.8024 }; // sekitar 1,6 km
const site = { id: "s-office", name: "Kantor Pusat", location: OFFICE, radius_m: 150, unit_id: null, can_manage: false };
const me = { ...mockMe("FINANCE")!, employee_id: "e-fin", attendance_mode: "OFFICE" } as Me;
const rec = {
  id: "a-fin", employee_id: "e-fin", work_date: "2026-10-02", site_id: site.id, site_label: site.name,
  check_in_at: "2026-10-02T01:00:00Z", check_out_at: null, distance_m: 12, is_late: false, is_early_leave: false,
  status: "AUTO_VALID", explanation: null, reviewed_at: null, employee_name: "Agus", selfie_file_id: null, can_review: false,
};

describe("OfficeCheckInCard: pulang di luar zona", () => {
  beforeEach(() => {
    vi.stubGlobal("navigator", {
      ...navigator,
      geolocation: {
        getCurrentPosition: (ok: PositionCallback) =>
          ok({ coords: { latitude: FAR.lat, longitude: FAR.lng, accuracy: 20 } } as GeolocationPosition),
      },
    });
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-10-02T11:30:00Z") });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("meminta penjelasan sebelum kirim, tanpa memanggil server", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/attendance") return { data: { items: [rec], total: 1, page: 1, size: 50, today: "2026-10-02" } };
      if (c.url === "/offices") return { data: [site] };
      if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
      if (c.url === "/attendance/check-out") return { data: { ...rec, check_out_at: "2026-10-02T10:00:00Z" } };
    });
    renderRoute("/attendance", { me });
    const region = await screen.findByRole("region", { name: "Absen hari ini" });
    fireEvent.click(await within(region).findByRole("button", { name: "Absen pulang" }));
    expect(await within(region).findByText(/Isi penjelasan mengapa pulang di luar zona/)).toBeInTheDocument();
    const field = within(region).getByLabelText("Penjelasan (wajib)");
    expect(field).toHaveAttribute("aria-invalid", "true"); // E6-2: galat di kolom
    expect(field).toHaveFocus();
    expect(calls.some((c) => c.url === "/attendance/check-out")).toBe(false);
  });
});

describe("OfficeCheckInCard: absen masuk perlu ditinjau (E6)", () => {
  beforeEach(() => {
    vi.stubGlobal("navigator", { ...navigator });
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-10-02T03:00:00Z") });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("catatan wajah belum terdaftar tetap tampil di kartu", async () => {
    const pending = { ...rec, status: "NEEDS_REVIEW", face_status: "NOT_ENROLLED" };
    mockApi((c) => {
      if (c.url === "/attendance") return { data: { items: [pending], total: 1, page: 1, size: 50, today: "2026-10-02" } };
      if (c.url === "/offices") return { data: [site] };
      if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    });
    renderRoute("/attendance", { me });
    const region = await screen.findByRole("region", { name: "Absen hari ini" });
    expect(await within(region).findByText(/Wajah Anda belum terdaftar/)).toBeInTheDocument();
  });
});

describe("Daftar absensi: filter Perlu ditinjau kosong (E6-3)", () => {
  it("menjelaskan bahwa absen sendiri ditinjau atasan", async () => {
    const reviewer = { ...me, permissions: [...me.permissions, "review:attendance", "view:all_attendance"] } as Me;
    mockApi((c) => {
      if (c.url === "/attendance") return { data: { items: [], total: 0, page: 1, size: 50, today: "2026-10-02" } };
      if (c.url === "/offices") return { data: [site] };
      if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    });
    renderRoute("/attendance", { me: reviewer });
    expect(await screen.findByText(/Absen Anda sendiri ditinjau oleh atasan/)).toBeInTheDocument();
  });
});
