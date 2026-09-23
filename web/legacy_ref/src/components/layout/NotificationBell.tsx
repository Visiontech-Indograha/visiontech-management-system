import { useState } from "react";
import { Bell } from "lucide-react";
import {
  useNotifications,
  useUnreadNotificationCount,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
} from "../../hooks/api/useNotifications";

const TYPE_ICON_COLOR: Record<string, string> = {
  DOCUMENT_EXPIRING: "bg-red-500",
  APPROVAL_PENDING: "bg-amber-500",
  WORK_PLAN_DUE: "bg-indigo-500",
  LEAVE_APPROVED: "bg-green-500",
  LEAVE_REJECTED: "bg-red-500",
};

export const NotificationBell = () => {
  const [open, setOpen] = useState(false);
  const { data: unreadCount } = useUnreadNotificationCount();
  const { data: notifications } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative rounded-full p-2 text-gray-500 hover:bg-gray-100"
        aria-label="Notifikasi"
      >
        <Bell className="h-5 w-5" />
        {!!unreadCount && unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-40 mt-2 w-80 max-w-[90vw] rounded-lg border border-gray-200 bg-white shadow-lg">
            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2">
              <span className="text-sm font-semibold text-gray-700">Notifikasi</span>
              {!!unreadCount && unreadCount > 0 && (
                <button
                  onClick={() => markAllRead.mutate()}
                  className="text-xs text-indigo-600 hover:underline"
                >
                  Tandai semua dibaca
                </button>
              )}
            </div>
            <div className="max-h-96 overflow-y-auto">
              {!notifications || notifications.length === 0 ? (
                <p className="p-4 text-center text-sm text-gray-400">Tidak ada notifikasi.</p>
              ) : (
                <ul className="divide-y divide-gray-100">
                  {notifications.map((n) => (
                    <li
                      key={n.id}
                      onClick={() => !n.is_read && markRead.mutate(n.id)}
                      className={`cursor-pointer px-4 py-3 hover:bg-gray-50 ${n.is_read ? "" : "bg-indigo-50/50"}`}
                    >
                      <div className="flex items-start gap-2">
                        <span className={`mt-1 h-2 w-2 flex-shrink-0 rounded-full ${TYPE_ICON_COLOR[n.type] || "bg-gray-400"}`} />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-gray-800">{n.title}</p>
                          {n.body && <p className="mt-0.5 text-xs text-gray-500">{n.body}</p>}
                          <p className="mt-1 text-[10px] text-gray-400">{new Date(n.created_at).toLocaleString()}</p>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
