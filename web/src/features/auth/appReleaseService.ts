import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export type AndroidRelease = {
  latest_build: number | null;
  latest_version: string | null;
  download: { size: number } | null;
};

/** GET /app/android/update?build=0 — rilis APK terbaru di portal (publik). Galat diabaikan: tautan cukup tidak tampil. */
export function useLatestAndroidRelease() {
  return useQuery({
    queryKey: ["app-android-latest"],
    queryFn: async () =>
      (await api.get<AndroidRelease>("/app/android/update", { params: { build: 0, abi: "arm64-v8a" } })).data,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
