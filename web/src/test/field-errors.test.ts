import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/apiClient";
import { applyFieldErrors, translateFieldMessage } from "@/lib/errors";

describe("translateFieldMessage", () => {
  it.each([
    ["String should have at most 150 characters", "Maksimal 150 karakter."],
    ["String should have at least 2 characters", "Minimal 2 karakter."],
    ["Field required", "Isian ini wajib diisi."],
    ["String should match pattern '^x$'", "Format isian belum sesuai."],
    ["Input should be greater than or equal to 10", "Nilai minimal 10."],
    ["Input should be less than 5", "Nilai harus lebih kecil dari 5."],
    ["Input should be a valid integer", "Isi dengan angka yang benar."],
    ["Value error, sesuatu", "Isian tidak valid. Periksa panjang atau format."],
    ["Nama sudah dipakai.", "Nama sudah dipakai."],
    [undefined, "Isian tidak valid. Periksa panjang atau format."],
  ])("%s", (raw, out) => expect(translateFieldMessage(raw)).toBe(out));

  it("dipakai oleh applyFieldErrors", () => {
    const setError = vi.fn();
    const err = new ApiError("VALIDATION_ERROR", "x", 422, { fields: { full_name: "String should have at most 150 characters" } });
    applyFieldErrors(err, setError);
    expect(setError.mock.calls[0][1].message).toBe("Maksimal 150 karakter.");
  });
});

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
