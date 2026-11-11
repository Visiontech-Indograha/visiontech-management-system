import { appEnv, ENV_LABEL, type AppEnv } from "@/lib/appEnv";

/** Penanda lingkungan non-produksi: pil tipis tetap di atas, tidak menangkap klik, tanpa mengubah tata letak. */
export function EnvBanner({ env = appEnv() }: { env?: AppEnv }) {
  if (!env) return null;
  const warna = env === "development" ? "bg-env-dev" : "bg-env-beta";
  return (
    <div
      role="status"
      data-testid="env-banner"
      className={`pointer-events-none fixed top-0 left-1/2 z-[1000] -translate-x-1/2 rounded-b-md px-3 py-0.5 text-xs font-semibold text-white ${warna}`}
    >
      {ENV_LABEL[env]}
    </div>
  );
}
