import type { ComponentProps } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { ExpiringDocumentsCard } from "@/components/organisms/home/ExpiringDocumentsCard";
import { HomeGreeting } from "@/components/organisms/home/HomeGreeting";
import { HomeStatGrid } from "@/components/organisms/home/HomeStatGrid";
import { HomeBentoDashboard } from "@/components/organisms/home/HomeBentoDashboard";
import type { ExpiringList } from "@/services/homeService";
import type { WorkPlan } from "@/services/workPlanService";

/** Kerangka Beranda: sapaan, Bento UI dashboard operasional, dokumen kedaluwarsa (HR/GA). */
export function HomeTemplate({ today, name, stats, canManageDocs, expiringDocs, plans }: {
  today: string;
  name: string | undefined;
  stats: ComponentProps<typeof HomeStatGrid>;
  canManageDocs: boolean;
  expiringDocs: ExpiringList["items"] | undefined;
  plans: UseQueryResult<WorkPlan[]>;
  active: WorkPlan[];
}) {
  const planList = plans.data ?? [];

  return (
    <div className="space-y-6 md:space-y-8">
      <header>
        <HomeGreeting today={today} name={name} />
      </header>

      {/* Bento UI Dashboard Eksekutif & Operasional */}
      <HomeBentoDashboard
        plans={planList}
        runningCount={stats.running.value ?? 0}
        waitingCount={stats.waiting.value ?? 0}
        reviewAttendanceCount={stats.toReview.value ?? 0}
        canCreatePlan={stats.canCreatePlan}
      />

      {/* Dokumen karyawan kedaluwarsa (HR/GA) */}
      {canManageDocs && !!expiringDocs?.length && <ExpiringDocumentsCard items={expiringDocs} />}
    </div>
  );
}
