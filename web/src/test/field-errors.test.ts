import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/apiClient";
import { applyFieldErrors } from "@/lib/errors";

describe("applyFieldErrors", () => {
  it("memetakan galat 422 ke kolom", () => {
    const setError = vi.fn();
    const err = new ApiError("VALIDATION_ERROR", "x", 422, { fields: { name: "too long", client_code: "bad" } });
    expect(applyFieldErrors(err, setError)).toBe(true);
    expect(setError).toHaveBeenCalledTimes(2);
    expect(setError.mock.calls[0][0]).toBe("name");
  });

  it("mengabaikan galat selain 422 atau tanpa fields", () => {
    const setError = vi.fn();
    expect(applyFieldErrors(new ApiError("X", "x", 500, {}), setError)).toBe(false);
    expect(applyFieldErrors(new ApiError("VALIDATION_ERROR", "x", 422, {}), setError)).toBe(false);
    expect(applyFieldErrors(new Error("x"), setError)).toBe(false);
    expect(setError).not.toHaveBeenCalled();
  });
});
