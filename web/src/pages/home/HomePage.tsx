import { useSession } from "@/stores/sessionStore";
import { HomeTemplate } from "@/components/templates/home/HomeTemplate";
import { useAttendanceToReview, useExpiringDocuments } from "@/services/homeService";
import { addDays, useDailyPlans, wibDate, weekStart } from "@/services/dailyPlanService";

/** Beranda (R-12, daily-first): sapaan, ringkasan jadwal minggu ini, jadwal aktif, dokumen kedaluwarsa. */
export function HomePage() {
  const { me } = useSession();
  const perms = me?.permissions ?? [];
  const canReview = perms.includes("review:attendance");
  const canCreatePlan = perms.includes("create:plan");
  const todayIso = wibDate();
  const start = weekStart(todayIso);
  const plans = useDailyPlans({ start, end: addDays(start, 6) });
  const toReview = useAttendanceToReview(canReview);
  const canManageDocs = perms.includes("manage:employee_documents");
  const expiring = useExpiringDocuments(canManageDocs);

  const list = plans.data ?? [];
  const running = list.filter((p) => p.status === "ONGOING");
  const onToday = list.filter((p) => p.work_date === todayIso);
  const waiting = list.filter((p) => p.status === "SUBMITTED");
  const active = [...new Set([...running, ...onToday, ...waiting])].slice(0, 6);
  const today = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" }).format(new Date());

  return (
    <HomeTemplate
      today={today}
      name={me?.email.split("@")[0]}
      stats={{
        running: { value: running.length, loading: plans.isPending },
        waiting: { value: waiting.length, loading: plans.isPending },
        today: { value: onToday.length, loading: plans.isPending },
        toReview: { value: toReview.data, loading: toReview.isPending },
        expiring: { value: expiring.data?.length, loading: expiring.isPending },
        canCreatePlan,
        canReview,
        canManageDocs,
      }}
      canManageDocs={canManageDocs}
      expiringDocs={expiring.data}
      plans={plans}
      active={active}
    />
  );
}
