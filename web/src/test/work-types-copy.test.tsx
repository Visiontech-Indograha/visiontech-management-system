import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

const FTTX = "11111111-2222-3333-4444-555555555555";
const MEP = "22222222-3333-4444-5555-666666666666";

const workType = {
  id: "wt-01",
  name: "Penyambungan Kabel FO",
  division_id: FTTX,
  division_name: "Fiber Optic",
  description: null,
  is_active: true,
  kind: "WORK",
  photos: [],
};

describe("Salin jenis pekerjaan ke divisi lain", () => {
  it("mengirim POST copy-to-division dengan divisi tujuan yang dipilih", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-types" && c.method === "get") return { data: [workType] };
      if (c.url === "/divisions") {
        return { data: [
          { id: FTTX, code: "FTTX", name: "Fiber Optic" },
          { id: MEP, code: "MEP", name: "Mechanical Electrical" },
        ] };
      }
      if (c.url === `/work-types/wt-01/copy-to-division`) return { status: 201, data: { ...workType, id: "wt-copy" } };
    });

    renderRoute("/work-types", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Salin ke divisi" }));
    await screen.findByRole("option", { name: /Mechanical Electrical/ });
    fireEvent.change(screen.getByLabelText("Divisi tujuan"), { target: { value: MEP } });
    fireEvent.click(screen.getByRole("button", { name: "Salin" }));

    await waitFor(() => {
      const post = calls.find((c) => c.method === "post" && c.url === "/work-types/wt-01/copy-to-division");
      expect(post?.data).toEqual({ division_id: MEP });
    });
  });

  it("divisi asal tidak ditawarkan sebagai tujuan", async () => {
    mockApi((c) => {
      if (c.url === "/work-types" && c.method === "get") return { data: [workType] };
      if (c.url === "/divisions") {
        return { data: [
          { id: FTTX, code: "FTTX", name: "Fiber Optic" },
          { id: MEP, code: "MEP", name: "Mechanical Electrical" },
        ] };
      }
    });

    renderRoute("/work-types", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Salin ke divisi" }));
    await screen.findByRole("option", { name: /Mechanical Electrical/ });
    const select = screen.getByLabelText("Divisi tujuan") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).not.toContain(FTTX);
    expect(values).toContain(MEP);
  });
});
