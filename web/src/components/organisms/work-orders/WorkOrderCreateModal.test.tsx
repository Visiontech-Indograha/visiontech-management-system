import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { WorkOrderCreateModal } from "@/components/organisms/work-orders/WorkOrderCreateModal";
import { useSession } from "@/stores/sessionStore";
import { apiError, mockApi } from "@/test/utils";

const DIV = "11111111-1111-4111-8111-111111111111";

function setup(pm: { status?: number; data: unknown }) {
  useSession.setState({ me: { ...mockMe("PM"), division_id: DIV, managed_division_ids: [DIV] } as never, ready: true });
  const calls = mockApi((c) => {
    if (c.url === "/work-orders/pm-candidates") return pm;
    if (c.url === "/divisions") return { data: [{ id: DIV, name: "Jaringan" }] };
    if (c.url === "/employees") return { data: { items: [], total: 0 } }; // PM tak melihat peran: kode lama kosong
    return { data: [] };
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <WorkOrderCreateModal isOpen onClose={() => {}} defaultDivisionId={DIV} />
    </QueryClientProvider>,
  );
  return calls;
}

describe("pilihan PM di Buat Tugas Klien", () => {
  it("memakai endpoint kandidat PM per divisi dan menampilkan namanya", async () => {
    const calls = setup({ data: [{ employee_id: "e1", full_name: "Budi PM", division_id: DIV, division_name: "Jaringan" }] });
    expect(await screen.findByRole("option", { name: "Budi PM" })).toBeInTheDocument();
    const c = calls.find((x) => x.url === "/work-orders/pm-candidates");
    expect(c?.params).toMatchObject({ division_id: DIV });
  });
  it("kosong: pesan awam", async () => {
    setup({ data: [] });
    expect(await screen.findByText("Belum ada PM di divisi ini")).toBeInTheDocument();
  });
  it("galat: pesan galat tampil", async () => {
    setup(apiError(500, "SERVER", "x"));
    expect(await screen.findByText(/Daftar PM belum bisa dimuat/)).toBeInTheDocument();
  });
});
