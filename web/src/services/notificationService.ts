import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type NotificationList = components["schemas"]["NotificationList"];

/** GET /notifications — 20 notifikasi terbaru + jumlah belum dibaca. */
export async function fetchNotifications(): Promise<NotificationList> {
  return (await api.get<NotificationList>("/notifications", { params: { limit: 20 } })).data;
}

/** Tandai satu notifikasi (`id`) atau semuanya (`null`) sudah dibaca. */
export async function markNotificationsRead(id: string | null): Promise<void> {
  await api.post(id ? `/notifications/${id}/read` : "/notifications/read-all");
}
