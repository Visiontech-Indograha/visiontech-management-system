import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EnvBanner } from "@/components/atoms/EnvBanner";

describe("EnvBanner", () => {
  it("tampil hanya bila bukan produksi", () => {
    const { rerender } = render(<EnvBanner env={null} />);
    expect(screen.queryByTestId("env-banner")).toBeNull();
    rerender(<EnvBanner env="development" />);
    expect(screen.getByTestId("env-banner").textContent).toBe("LINGKUNGAN DEV · bukan data produksi");
    rerender(<EnvBanner env="beta" />);
    expect(screen.getByTestId("env-banner").textContent).toContain("BETA");
  });
});
