import type { UseQueryResult } from "@tanstack/react-query";
import { ArrowRight, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/atoms/Card";
import { Skeleton } from "@/components/atoms/Skeleton";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate } from "@/lib/format";
import type { WorkPlan } from "@/services/workPlanService";

/** "Pekerjaan aktif": permintaan revisi, rencana berjalan, lalu yang menunggu tindakan (maks. 6). */
export function HomeActivePlansCard({ plans, active }: { plans: UseQueryResult<WorkPlan[]>; active: WorkPlan[] }) {
  return (
      <Card className="gap-4">
        <CardHeader>
          <CardTitle className="text-heading">Pekerjaan aktif</CardTitle>
          <CardDescription>Rencana Kerja berjalan dan yang menunggu tindakan.</CardDescription>
        </CardHeader>
        <CardContent className="px-3 md:px-4">
          {plans.isPending && <Skeleton className="mx-3 h-14" />}
          {plans.isError && <p className="px-3 text-danger">Daftar rencana kerja tidak dapat dimuat.</p>}
          {plans.isSuccess && active.length === 0 && <p className="px-3 text-mist">Belum ada rencana kerja aktif.</p>}
          <ul className="divide-y divide-line">
            {active.map((p) => (
              <li key={p.id}>
                <Link
                  to={`/work-plans/${p.id}`}
                  className="group flex items-center gap-4 rounded-control px-3 py-3 transition-colors hover:bg-hover"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-ink">{p.title}</p>
                    <p className="mt-0.5 flex items-center gap-1.5 truncate text-body-sm text-mist">
                      <MapPin size={14} aria-hidden className="shrink-0" />
                      {p.location_text} · {formatDate(p.period_start)} – {formatDate(p.period_end)}
                    </p>
                  </div>
                  <StatusBadge status={p.status} />
                  <ArrowRight size={18} aria-hidden className="shrink-0 text-mist transition-transform duration-300 group-hover:translate-x-1" />
                </Link>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
  );
}
