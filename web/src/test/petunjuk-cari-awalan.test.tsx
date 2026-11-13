import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

describe("petunjuk pencarian", () => {
  it("placeholder email login tidak berubah", async () => {
    mockApi(() => undefined);
    renderRoute("/login", { role: null });
    expect(await screen.findByPlaceholderText("nama@visiontech.id")).toBeInTheDocument();
  });
});
