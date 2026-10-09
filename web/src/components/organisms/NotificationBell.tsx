import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { useNavigate } from "react-router-dom";
import { formatDateTime } from "@/lib/format";
import { Menu, MenuContent, MenuItem, MenuLabel, MenuSeparator, MenuTrigger } from "@/components/molecules/Menu";
import { Bell } from "@/components/molecules/Glyphs";
import { TextBlock } from "@/components/molecules/TextBlock";
import { PlainAction } from "@/components/molecules/PlainAction";
import { fetchNotifications, markNotificationsRead } from "@/services/notificationService";

const KEY = ["notifications"] as const;

/** Lonceng notifikasi dalam aplikasi (alur SK v2): diperiksa tiap 60 detik, klik membuka SK terkait. */
export function NotificationBell({ className }: { className?: string }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const list = useQuery({
    queryKey: KEY,
    queryFn: fetchNotifications,
    refetchInterval: 60_000,
  });
  const read = useMutation({
    mutationFn: markNotificationsRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
  const unread = list.data?.unread ?? 0;

  return (
    <Menu>
      <MenuTrigger
        className={clsx("relative rounded-control p-2 text-ink hover:bg-hover", className)}
        aria-label={unread ? `Notifikasi, ${unread} belum dibaca` : "Notifikasi"}
      >
        <Bell size={20} />
        {unread > 0 && (
          <TextBlock as="span" className="absolute -right-0.5 -top-0.5 grid min-w-5 place-items-center rounded-full bg-danger px-1 text-[11px] font-semibold text-white">
            {unread > 99 ? "99+" : unread}
          </TextBlock>
        )}
      </MenuTrigger>
      <MenuContent align="end" className="w-[min(22rem,calc(100vw-2rem))]">
        <div className="flex items-center justify-between px-2 py-1.5">
          <MenuLabel className="p-0">Notifikasi</MenuLabel>
          {unread > 0 && (
            <PlainAction type="button" className="text-xs font-medium text-lens hover:underline" onClick={() => read.mutate(null)}>
              Tandai semua dibaca
            </PlainAction>
          )}
        </div>
        <MenuSeparator />
        {list.isError && <TextBlock className="px-2 py-3 text-sm text-danger">Notifikasi tidak dapat dimuat.</TextBlock>}
        {list.data?.items.length === 0 && <TextBlock className="px-2 py-3 text-sm text-mist">Belum ada notifikasi.</TextBlock>}
        <div className="max-h-96 overflow-y-auto">
          {list.data?.items.map((n) => (
            <MenuItem
              key={n.id}
              className="flex flex-col items-start gap-0.5 py-2"
              onSelect={() => {
                if (!n.read_at) read.mutate(n.id);
                if (n.work_plan_id) navigate(`/work-plans/${n.work_plan_id}`);
              }}
            >
              <TextBlock as="span" className={clsx("text-sm", !n.read_at && "font-semibold text-ink")}>{n.title}</TextBlock>
              {n.body && <TextBlock as="span" className="text-xs text-mist">{n.body}</TextBlock>}
              <TextBlock as="span" className="text-xs text-mist">{formatDateTime(n.created_at)}</TextBlock>
            </MenuItem>
          ))}
        </div>
      </MenuContent>
    </Menu>
  );
}
