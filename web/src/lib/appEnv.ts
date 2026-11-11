export type AppEnv = "development" | "beta" | null;

/** Lingkungan dari variabel build Vite. Produksi (atau tak diatur) = null: tanpa penanda. */
export function appEnv(
  env: { VITE_APP_ENV?: string; MODE?: string } = import.meta.env,
): AppEnv {
  const v = env.VITE_APP_ENV ?? (env.MODE === "development" ? "development" : "");
  return v === "development" || v === "beta" ? v : null;
}

export const ENV_LABEL = {
  development: "LINGKUNGAN DEV · bukan data produksi",
  beta: "LINGKUNGAN BETA · bukan data produksi",
} as const;

export const ENV_TITLE_PREFIX = { development: "[DEV] ", beta: "[BETA] " } as const;
