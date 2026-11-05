import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { idempotencyHeaders, useIdempotencyKey } from "@/lib/idempotency";
import { applyLeave } from "@/services/leaveService";

describe("kunci idempotensi", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("stabil selama isi sama, berganti saat isi berubah atau setelah renew", () => {
    const { result, rerender } = renderHook(({ s }) => useIdempotencyKey(s), { initialProps: { s: "a" } });
    const first = result.current.key;
    rerender({ s: "a" });
    expect(result.current.key).toBe(first);
    expect(result.current.keyFor(2)).toBe(`${first}:2`);
    rerender({ s: "b" });
    expect(result.current.key).not.toBe(first);
    const second = result.current.key;
    act(() => result.current.renew());
    rerender({ s: "b" });
    expect(result.current.key).not.toBe(second);
  });

  it("header dikirim ulang dengan kunci yang sama pada retry", async () => {
    const post = vi.spyOn(api, "post").mockResolvedValue({ data: {} });
    const body = { leave_type: "ANNUAL", start_date: "2026-01-01", end_date: "2026-01-02", reason: "x" };
    await applyLeave({ ...body, idempotencyKey: "k-12345678" } as never);
    await applyLeave({ ...body, idempotencyKey: "k-12345678" } as never);
    expect(post.mock.calls[0][2]).toEqual({ headers: idempotencyHeaders("k-12345678") });
    expect(post.mock.calls[1][2]).toEqual(post.mock.calls[0][2]);
    expect(post.mock.calls[0][1]).not.toHaveProperty("idempotencyKey");
  });

  it("409 sedang diproses memberi pesan sederhana", () => {
    const err = new ApiError("IDEMPOTENCY_SEDANG_DIPROSES", "x", 409);
    expect(errorMessage(err)).toBe("Pengajuan sedang diproses, tunggu sebentar.");
  });
});
