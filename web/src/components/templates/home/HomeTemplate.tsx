import type { ComponentProps } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { ExpiringDocumentsCard } from "@/components/organisms/home/ExpiringDocumentsCard";
import { HomeActivePlansCard } from "@/components/organisms/home/HomeActivePlansCard";
import { HomeGreeting } from "@/components/organisms/home/HomeGreeting";
import { HomeStatGrid } from "@/components/organisms/home/HomeStatGrid";
import type { ExpiringList } from "@/services/homeService";
import type { DailyPlan } from "@/services/dailyPlanService";

/** Kerangka Beranda: sapaan, ringkasan jadwal harian, jadwal aktif, dokumen kedaluwarsa (HR/GA). */
export function HomeTemplate({ today, name, stats, canManageDocs, expiringDocs, plans, active }: {
  today: string;
  name: string | undefined;
  stats: ComponentProps<typeof HomeStatGrid>;
  canManageDocs: boolean;
  expiringDocs: ExpiringList["items"] | undefined;
  plans: UseQueryResult<DailyPlan[]>;
  active: DailyPlan[];
}) {
  return (
    <div className="space-y-6 md:space-y-8">
      <header>
        <HomeGreeting today={today} name={name} />
      </header>
      <HomeStatGrid {...stats} />
      <HomeActivePlansCard plans={plans} active={active} />
      {/* Dokumen karyawan kedaluwarsa (HR/GA) */}
      {canManageDocs && !!expiringDocs?.length && <ExpiringDocumentsCard items={expiringDocs} />}
    </div>
  );
}
