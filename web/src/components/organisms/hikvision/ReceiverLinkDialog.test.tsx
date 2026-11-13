import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReceiverLinkDialog } from "./ReceiverLinkDialog";

const link = { device_id: "d1", token: "rahasia", receiver_url: "https://vms.example/api/v1/hikvision/events/rahasia", receiver_path: "/x" };

describe("ReceiverLinkDialog", () => {
  it("menampilkan tautan dengan peringatan sekali tampil", () => {
    render(<ReceiverLinkDialog deviceName="Pintu depan" link={link} onClose={() => {}} />);
    expect(screen.getByText(/tidak akan ditampilkan lagi/i)).toBeInTheDocument();
    expect(screen.getByText(link.receiver_url)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salin tautan" })).toBeInTheDocument();
  });

  it("menyalin tautan ke clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(<ReceiverLinkDialog deviceName="Pintu depan" link={link} onClose={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Salin tautan" }));
    expect(writeText).toHaveBeenCalledWith(link.receiver_url);
  });
});
