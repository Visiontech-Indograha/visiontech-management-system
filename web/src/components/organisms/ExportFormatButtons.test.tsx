import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExportFormatButtons } from "@/components/organisms/ExportFormatButtons";
import { api, ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";

describe("ekspor: galat dan status klik", () => {
  it("tombol langsung nonaktif dan Menyiapkan setelah klik, walau induk belum busy", () => {
    const onPick = vi.fn();
    render(<ExportFormatButtons label="Laporan mingguan" busy={false} onPick={onPick} />);
    fireEvent.click(screen.getByRole("button", { name: "Laporan mingguan sebagai PDF" }));
    expect(onPick).toHaveBeenCalledWith("PDF");
    expect(screen.getByRole("button", { name: "Laporan mingguan sebagai PDF" })).toHaveTextContent("Menyiapkan");
    for (const b of screen.getAllByRole("button")) expect(b).toBeDisabled();
  });

  it("galat 422 pada unduhan blob dibaca jadi pesan awam API", async () => {
    const msg = "Belum ada pekerjaan tim ini pada minggu tersebut.";
    const body = new Blob([JSON.stringify({ error: { code: "NO_WORK", message: msg } })], { type: "application/json" });
    const err = await api
      .post("/exports/x", {}, {
        responseType: "blob",
        adapter: async (config) => {
          throw Object.assign(new Error("x"), {
            isAxiosError: true,
            config,
            response: { status: 422, data: body, headers: {}, config },
          });
        },
      })
      .catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(errorMessage(err)).toBe(msg);
  });
});
