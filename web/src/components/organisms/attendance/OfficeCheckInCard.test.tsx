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
    expect(await within(region).findByRole("alert")).toHaveTextContent(/Isi penjelasan mengapa pulang di luar zona/);
    expect(within(region).getByLabelText("Penjelasan (wajib)")).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/attendance/check-out")).toBe(false);
  });
});
