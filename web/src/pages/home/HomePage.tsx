import { useSession } from "@/app/session";
import { ExpiringDocumentsCard } from "@/components/organisms/home/ExpiringDocumentsCard";
import { HomeActivePlansCard } from "@/components/organisms/home/HomeActivePlansCard";
import { HomeGreeting } from "@/components/organisms/home/HomeGreeting";
import { HomeStatGrid } from "@/components/organisms/home/HomeStatGrid";
import { PendingDocumentsCard } from "@/components/organisms/home/PendingDocumentsCard";
import { useAttendanceToReview, useExpiringDocuments, usePendingDocuments } from "@/services/homeService";
import { useWorkPlans } from "@/services/workPlanService";

const WAITING = ["DRAFT", "PUBLISHED", "ACCEPTED", "APPEALED", "COMPLETION_REVIEW"];

/** Beranda (R-12): sapaan, ringkasan angka, rencana kerja aktif, antrean dokumen — semua dari endpoint yang sudah ada. */
export function HomePage() {
  const { me } = useSession();
  const perms = me?.permissions ?? [];
  const canReview = perms.includes("review:attendance");
  const plans = useWorkPlans({ status: "", archived: false });
  const toReview = useAttendanceToReview(canReview);
  const canVerifyDocs = perms.includes("verify:documents");
  const expiring = useExpiringDocuments(canVerifyDocs);
  const pending = usePendingDocuments(canVerifyDocs);

  const list = plans.data ?? [];
  const running = list.filter((p) => p.status === "IN_PROGRESS");
  const waiting = list.filter((p) => WAITING.includes(p.status) || p.pending_request);
  const requests = list.filter((p) => p.pending_request);
  const active = [...new Set([...requests, ...running, ...waiting])].slice(0, 6);
  const today = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" }).format(new Date());

  return (
    <div className="space-y-6 md:space-y-8">
      <header>
        <HomeGreeting today={today} name={me?.email.split("@")[0]} />
      </header>

      <HomeStatGrid
        running={{ value: running.length, loading: plans.isPending }}
        waiting={{ value: waiting.length, loading: plans.isPending }}
        requests={{ value: requests.length, loading: plans.isPending }}
        toReview={{ value: toReview.data, loading: toReview.isPending }}
        pending={{ value: pending.data?.length, loading: pending.isPending }}
        expiring={{ value: expiring.data?.length, loading: expiring.isPending }}
        canCreatePlan={perms.includes("create:plan")}
        canReview={canReview}
        canVerifyDocs={canVerifyDocs}
      />

      {canVerifyDocs && !!pending.data?.length && <PendingDocumentsCard items={pending.data} />}
      {canVerifyDocs && !!expiring.data?.length && <ExpiringDocumentsCard items={expiring.data} />}

      <HomeActivePlansCard plans={plans} active={active} />
    </div>
  );
}
