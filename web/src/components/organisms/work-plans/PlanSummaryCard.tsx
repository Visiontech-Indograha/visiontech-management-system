import type { ReactNode } from "react";
import { CATEGORY_LABEL } from "@/lib/labels";
import { formatDate } from "@/lib/format";
import { employeeName, type WorkPlan } from "@/services/workPlanService";

const Row = ({ label, children }: { label: string; children: ReactNode }) => (
  <div className="flex flex-col gap-0.5 border-b border-line py-2 last:border-0 md:flex-row md:justify-between md:gap-4">
    <dt className="text-mist">{label}</dt>
    <dd className="font-medium md:text-right">{children}</dd>
  </div>
);

/** Rincian pokok rencana kerja: nomor, revisi, lokasi, periode, PM, ketua, deskripsi, alasan revisi/pembatalan. */
export function PlanSummaryCard({ plan: p, employees }: { plan: WorkPlan; employees: Parameters<typeof employeeName>[0] }) {
  return (
            <section aria-label="Rincian rencana kerja" className="rounded-panel border border-line bg-surface shadow-card px-5 py-2">
              <dl className="text-sm">
                <Row label="Nomor rencana kerja">{p.number ?? "Belum terbit"}</Row>
                <Row label="Revisi">{p.revision}</Row>
                {p.is_out_of_town && <Row label="Jenis">Luar kota</Row>}
                {p.category && <Row label="Kategori">{CATEGORY_LABEL[p.category] ?? p.category}</Row>}
                <Row label="Lokasi">{p.location_text}</Row>
                <Row label="Periode">
                  {formatDate(p.period_start)} – {formatDate(p.period_end)}
                </Row>
                <Row label="PM">{employeeName(employees, p.pm_employee_id)}</Row>
                <Row label="Ketua tim">{employeeName(employees, p.leader_employee_id)}</Row>
                {p.description && <Row label="Deskripsi pekerjaan">{p.description}</Row>}
                {p.appeal_reason && <Row label="Alasan revisi">{p.appeal_reason}</Row>}
                {p.cancellation_reason && <Row label="Alasan pembatalan">{p.cancellation_reason}</Row>}
              </dl>
            </section>
  );
}
