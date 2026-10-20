import { useSession } from "@/stores/sessionStore";
import { HomeTemplate } from "@/components/templates/home/HomeTemplate";
import { useAttendanceToReview, useExpiringDocuments } from "@/services/homeService";
import { useWorkPlans } from "@/services/workPlanService";

const WAITING = ["DRAFT", "PUBLISHED", "ACCEPTED", "APPEALED", "COMPLETION_REVIEW"];

/** Beranda (R-12): sapaan, ringkasan angka, rencana kerja aktif, antrean dokumen — semua dari endpoint yang sudah ada. */
export function HomePage() {
  const { me } = useSession();
  const perms = me?.permissions ?? [];
  const canReview = perms.includes("review:attendance");
  const plans = useWorkPlans({ status: "", archived: false });
  const toReview = useAttendanceToReview(canReview);
  const canManageDocs = perms.includes("manage:employee_documents");
  const expiring = useExpiringDocuments(canManageDocs);

  const list = plans.data ?? [];
  const running = list.filter((p) => p.status === "IN_PROGRESS");
  const waiting = list.filter((p) => WAITING.includes(p.status) || p.pending_request);
  const requests = list.filter((p) => p.pending_request);
  const active = [...new Set([...requests, ...running, ...waiting])].slice(0, 6);
  const today = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" }).format(new Date());

  return (
    <HomeTemplate
      today={today}
      name={me?.email.split("@")[0]}
      stats={{
        running: { value: running.length, loading: plans.isPending },
        waiting: { value: waiting.length, loading: plans.isPending },
        requests: { value: requests.length, loading: plans.isPending },
        toReview: { value: toReview.data, loading: toReview.isPending },
        expiring: { value: expiring.data?.length, loading: expiring.isPending },
        canCreatePlan: perms.includes("create:plan"),
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
