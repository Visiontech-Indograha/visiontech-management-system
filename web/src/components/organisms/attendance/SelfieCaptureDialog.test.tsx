import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SelfieCaptureDialog } from "./SelfieCaptureDialog";

describe("SelfieCaptureDialog: akurasi lokasi", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("menampilkan akurasi dan penjelasan awam bila lokasi kasar", () => {
    Object.defineProperty(navigator, "mediaDevices", { value: undefined, configurable: true });
    render(
      <SelfieCaptureDialog
        info="Ambil swafoto"
        position={{ lat: 0.5, lng: 101.4, accuracy: 250 }}
        siteName="Kantor"
        onCancel={() => undefined}
        onCaptured={() => undefined}
      />,
    );
    expect(screen.getByText(/Akurasi lokasi ±250 m/)).toBeTruthy();
    expect(screen.getByText(/tanpa GPS/)).toBeTruthy();
  });
});
