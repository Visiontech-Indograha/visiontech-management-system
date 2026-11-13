import userEvent from "@testing-library/user-event";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { WorkOrderAssignModal } from "@/components/organisms/work-orders/WorkOrderAssignModal";
import { WorkOrderCreateModal, WO_TITLE_MAX } from "@/components/organisms/work-orders/WorkOrderCreateModal";
import { SidebarProfile } from "@/components/organisms/SidebarProfile";
import { LeaveApplyDialog } from "@/components/organisms/leaves/LeaveApplyDialog";
import { ApiError } from "@/lib/apiClient";
import { errorMessage, OFFBOARDING_OUT_OF_OFFICE_MESSAGE } from "@/lib/errors";
import { indonesianValidityMessage } from "@/lib/nativeValidity";
import { campaignPublishBlocker, HSE_TITLE_MAX } from "@/lib/hseCampaignRules";
import type { WorkOrder } from "@/services/workOrderService";
import { mockApi } from "./utils";

const wrap = (ui: React.ReactNode) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
};

const wo = {
  work_order_id: "wo1", wo_number: "WO-1", title: "Kabel putus", client_name: "PT A", site_name: null, lead_team_id: null,
} as unknown as WorkOrder;

describe("butir 1: dialog Tugaskan survei", () => {
  it("tanggal kosong memunculkan pesan Indonesia, bukan pesan bawaan browser", async () => {
    mockApi((c) => (c.url === "/teams" ? { data: [{ team_id: "t1", name: "Tim A", leader_name: "Budi" }] } : undefined));
    wrap(<WorkOrderAssignModal workOrder={wo} onClose={() => {}} />);
    await screen.findByRole("option", { name: /Tim A/ });
    await userEvent.selectOptions(screen.getByLabelText(/Pilih tim survei/), "t1");
    fireEvent.change(screen.getByLabelText(/Tanggal survei/), { target: { value: "" } });
    await userEvent.click(screen.getByRole("button", { name: "Tugaskan Tim Survei" }));
    expect(await screen.findByText("Tanggal survei wajib diisi agar tim bisa melihat tugasnya di HP.")).toBeInTheDocument();
  });

  it("setelah sukses, ringkasan penugasan tampil di layar", async () => {
    mockApi((c) => {
      if (c.url === "/teams") return { data: [{ team_id: "t1", name: "Tim A", leader_name: "Budi" }] };
      if (c.url === "/work-orders/wo1/assign-survey") {
        return { data: { survey_assignment_summary: "Tim Tim A akan melihat di HP pada tanggal 12-11-2026." } };
      }
      return undefined;
    });
    wrap(<WorkOrderAssignModal workOrder={wo} onClose={() => {}} />);
    await screen.findByRole("option", { name: /Tim A/ });
    await userEvent.selectOptions(screen.getByLabelText(/Pilih tim survei/), "t1");
    await userEvent.click(screen.getByRole("button", { name: "Tugaskan Tim Survei" }));
    expect(await screen.findByRole("status")).toHaveTextContent("akan melihat di HP pada tanggal 12-11-2026");
  });
});

describe("butir 2: pesan batas bawaan browser", () => {
  it("rangeUnderflow tanggal menjadi kalimat Indonesia", () => {
    const el = document.createElement("input");
    el.type = "date";
    el.min = "2026-11-08";
    el.value = "2026-11-01";
    expect(indonesianValidityMessage(el)).toBe("Tanggal tidak boleh sebelum 08-11-2026.");
  });

  it("angka di atas max dan kosong wajib memakai Indonesia", () => {
    const n = document.createElement("input");
    n.type = "number";
    n.max = "5";
    n.value = "9";
    expect(indonesianValidityMessage(n)).toBe("Nilai maksimal 5.");
    const r = document.createElement("input");
    r.required = true;
    expect(indonesianValidityMessage(r)).toBe("Isian ini wajib diisi.");
  });

  it("input atom memasang pesan Indonesia saat invalid", async () => {
    mockApi(() => undefined);
    wrap(<LeaveApplyDialog onClose={() => {}} />);
    const mulai = screen.getByLabelText("Tanggal Mulai") as HTMLInputElement;
    mulai.min = "2026-11-08";
    fireEvent.change(mulai, { target: { value: "2026-11-01" } });
    mulai.checkValidity();
    expect(mulai.validationMessage).toMatch(/^Tanggal tidak boleh sebelum/);
  });
});

describe("butir 3: batas judul", () => {
  it("judul WO memakai maxLength sama dengan API", () => {
    mockApi(() => ({ data: [] }));
    wrap(<WorkOrderCreateModal isOpen onClose={() => {}} />);
    expect(WO_TITLE_MAX).toBe(200);
    expect(screen.getByLabelText(/Judul Tugas/)).toHaveAttribute("maxlength", "200");
  });

  it("judul K3 maks 255 dan alasan Terbitkan jelas", () => {
    expect(HSE_TITLE_MAX).toBe(255);
    expect(campaignPublishBlocker("", "")).toBe("Isi judul dan isi kampanye dulu agar bisa diterbitkan.");
    expect(campaignPublishBlocker("A", "<p></p>")).toBe("Isi isi kampanye dulu agar bisa diterbitkan.");
    expect(campaignPublishBlocker("A", "<p>x</p>")).toBeNull();
  });
});

describe("butir 6: pesan proses keluar", () => {
  it("404 data proses keluar diganti pesan awam", () => {
    const err = new ApiError("NOT_FOUND", "Data proses keluar tidak ditemukan.", 404, {});
    expect(errorMessage(err)).toBe(OFFBOARDING_OUT_OF_OFFICE_MESSAGE);
    expect(OFFBOARDING_OUT_OF_OFFICE_MESSAGE).toBe(
      "Karyawan ini bukan dari kantor tugas Anda, jadi proses keluarnya tidak bisa Anda kelola.",
    );
  });
});

describe("butir 8: satu tombol Keluar", () => {
  it("hanya satu tombol bernama Keluar, juga saat konfirmasi terbuka", async () => {
    render(
      <MemoryRouter>
        <QueryClientProvider client={new QueryClient()}>
          <SidebarProfile email="a@visiontech.id" roleLabel="HR" collapsed={false} onLogout={vi.fn()} />
        </QueryClientProvider>
      </MemoryRouter>,
    );
    expect(screen.getAllByRole("button", { name: "Keluar" })).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: "Keluar" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Ya, keluar" })).toBeInTheDocument());
    expect(screen.queryAllByRole("button", { name: "Keluar" }).length).toBeLessThanOrEqual(1);
  });
});
