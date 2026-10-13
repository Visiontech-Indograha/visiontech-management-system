import type { ComponentProps } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { ExpiringDocumentsCard } from "@/components/organisms/home/ExpiringDocumentsCard";
import { HomeActivePlansCard } from "@/components/organisms/home/HomeActivePlansCard";
import { HomeGreeting } from "@/components/organisms/home/HomeGreeting";
import { HomeStatGrid } from "@/components/organisms/home/HomeStatGrid";
import { PendingDocumentsCard } from "@/components/organisms/home/PendingDocumentsCard";
import type { ExpiringList, PendingList } from "@/services/homeService";
import type { WorkPlan } from "@/services/workPlanService";

/** Kerangka Beranda: sapaan, kartu angka, antrean dokumen (HR), rencana kerja aktif. */
export function HomeTemplate({ today, name, stats, canVerifyDocs, pendingDocs, expiringDocs, plans, active }: {
  today: string;
  name: string | undefined;
  stats: ComponentProps<typeof HomeStatGrid>;
  canVerifyDocs: boolean;
  pendingDocs: PendingList["items"] | undefined;
  expiringDocs: ExpiringList["items"] | undefined;
  plans: UseQueryResult<WorkPlan[]>;
  active: WorkPlan[];
}) {
  return (
    <div className="space-y-6 md:space-y-8">
      <header>
        <HomeGreeting today={today} name={name} />
      </header>

      <HomeStatGrid {...stats} />

      {canVerifyDocs && !!pendingDocs?.length && <PendingDocumentsCard items={pendingDocs} />}
      {canVerifyDocs && !!expiringDocs?.length && <ExpiringDocumentsCard items={expiringDocs} />}

      <HomeActivePlansCard plans={plans} active={active} />
    </div>
  );
}
