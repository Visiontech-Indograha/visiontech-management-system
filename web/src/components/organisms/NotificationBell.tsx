import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { Bell } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/atoms/DropdownMenu";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { formatDateTime } from "@/lib/format";

type NotificationList = components["schemas"]["NotificationList"];
const KEY = ["notifications"] as const;

/** Lonceng notifikasi dalam aplikasi (alur SK v2): diperiksa tiap 60 detik, klik membuka SK terkait. */
export function NotificationBell({ className }: { className?: string }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const list = useQuery({
    queryKey: KEY,
    queryFn: async () => (await api.get<NotificationList>("/notifications", { params: { limit: 20 } })).data,
    refetchInterval: 60_000,
  });
  const read = useMutation({
    mutationFn: async (id: string | null) => api.post(id ? `/notifications/${id}/read` : "/notifications/read-all"),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
  const unread = list.data?.unread ?? 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={clsx("relative rounded-control p-2 text-ink hover:bg-hover", className)}
        aria-label={unread ? `Notifikasi, ${unread} belum dibaca` : "Notifikasi"}
      >
        <Bell size={20} />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 grid min-w-5 place-items-center rounded-full bg-danger px-1 text-[11px] font-semibold text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[min(22rem,calc(100vw-2rem))]">
        <div className="flex items-center justify-between px-2 py-1.5">
          <DropdownMenuLabel className="p-0">Notifikasi</DropdownMenuLabel>
          {unread > 0 && (
            <button type="button" className="text-xs font-medium text-lens hover:underline" onClick={() => read.mutate(null)}>
              Tandai semua dibaca
            </button>
          )}
        </div>
        <DropdownMenuSeparator />
        {list.isError && <p className="px-2 py-3 text-sm text-danger">Notifikasi tidak dapat dimuat.</p>}
        {list.data?.items.length === 0 && <p className="px-2 py-3 text-sm text-mist">Belum ada notifikasi.</p>}
        <div className="max-h-96 overflow-y-auto">
          {list.data?.items.map((n) => (
            <DropdownMenuItem
              key={n.id}
              className="flex flex-col items-start gap-0.5 py-2"
              onSelect={() => {
                if (!n.read_at) read.mutate(n.id);
                if (n.work_plan_id) navigate(`/work-plans/${n.work_plan_id}`);
              }}
            >
              <span className={clsx("text-sm", !n.read_at && "font-semibold text-ink")}>{n.title}</span>
              {n.body && <span className="text-xs text-mist">{n.body}</span>}
              <span className="text-xs text-mist">{formatDateTime(n.created_at)}</span>
            </DropdownMenuItem>
          ))}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
