import { test as base, expect } from "@playwright/test";
import { API_URL } from "./env";

/**
 * Setiap login membuka satu "perangkat" (batas 4 per akun). Fixture ini mengeluarkan sesi
 * tiap konteks peramban sesudah tes agar jalan berulang tidak mentok di batas perangkat.
 */
export const test = base.extend({
  context: async ({ context }, pakai) => {
    await pakai(context);
    await context.request.post(`${API_URL}/auth/logout`, { timeout: 3000 }).catch(() => undefined);
  },
});

export { expect };
