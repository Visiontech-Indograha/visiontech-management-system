import { Smartphone } from "lucide-react";
import { useLatestAndroidRelease } from "@/services/appReleaseService";

/** Tautan pemasangan pertama aplikasi HP (docs/32) — hanya tampil bila sudah ada rilis di portal. */
export function AndroidAppLink() {
  const { data } = useLatestAndroidRelease();
  if (!data?.latest_build || !data.download) return null;
  const mb = (data.download.size / (1024 * 1024)).toFixed(0);
  return (
    <a
      href={`${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1/app/android/latest.apk`}
      className="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm font-medium text-primary hover:underline"
      data-testid="unduh-aplikasi-android"
    >
      <Smartphone aria-hidden className="size-4" />
      Unduh aplikasi Android · versi {data.latest_version} (build {data.latest_build}) · {mb} MB
    </a>
  );
}
