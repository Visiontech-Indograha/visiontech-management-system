import { SystemStatusMessage } from "@/components/organisms/system/SystemStatusMessage";

/** Kerangka halaman status sistem (akses ditolak, tidak ditemukan). */
export function SystemStatusTemplate({ title, description }: { title: string; description?: string }) {
  return <SystemStatusMessage title={title} description={description} />;
}
