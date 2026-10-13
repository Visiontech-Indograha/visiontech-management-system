import type { ReactNode } from "react";
import { Panel, PanelContent } from "@/components/molecules/Panel";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { CalendarClock, ClipboardCheck, FileCheck2, FileClock, FileWarning } from "@/components/molecules/Glyphs";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";

type Count = { value: number | undefined; loading: boolean };

function Stat({ label, value, icon, to, loading }: { label: string; value: number | undefined; icon: ReactNode; to: string; loading: boolean }) {
  return (
    <InlineLink to={to} className="group block rounded-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
      <Panel className="h-full gap-3 py-5">
        <PanelContent className="flex items-start justify-between gap-3 px-5">
          <div>
            <TextBlock className="text-body-sm text-mist">{label}</TextBlock>
            {loading ? <LoadingBar className="mt-2 h-8 w-12" /> : <TextBlock className="mt-1 text-display text-ink">{value ?? 0}</TextBlock>}
          </div>
          <TextBlock as="span" className="grid size-10 place-items-center rounded-control bg-accent text-lens transition-transform duration-300 group-hover:scale-110" aria-hidden>
            {icon}
          </TextBlock>
        </PanelContent>
      </Panel>
    </InlineLink>
  );
}

/** Kartu angka ringkasan Beranda; kartu yang butuh izin hanya tampil bila diizinkan. */
export function HomeStatGrid({ running, waiting, requests, toReview, pending, expiring, canCreatePlan, canReview, canVerifyDocs }: {
  running: Count;
  waiting: Count;
  requests: Count;
  toReview: Count;
  pending: Count;
  expiring: Count;
  canCreatePlan: boolean;
  canReview: boolean;
  canVerifyDocs: boolean;
}) {
  return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Stat label="Rencana Kerja berjalan" value={running.value} loading={running.loading} icon={<CalendarClock size={20} />} to="/work-plans" />
        <Stat label="Rencana Kerja menunggu tindakan" value={waiting.value} loading={waiting.loading} icon={<FileClock size={20} />} to="/work-plans" />
        {canCreatePlan && (
          <Stat label="Permintaan revisi dari ketua" value={requests.value} loading={requests.loading} icon={<FileClock size={20} />} to="/work-plans" />
        )}
        {canReview && (
          <Stat label="Absensi perlu diperiksa" value={toReview.value} loading={toReview.loading} icon={<ClipboardCheck size={20} />} to="/attendance" />
        )}
        {canVerifyDocs && (
          <Stat label="Dokumen menunggu verifikasi" value={pending.value} loading={pending.loading} icon={<FileCheck2 size={20} />} to="/directory" />
        )}
        {canVerifyDocs && (
          <Stat label="Dokumen mendekati kedaluwarsa" value={expiring.value} loading={expiring.loading} icon={<FileWarning size={20} />} to="/directory" />
        )}
      </div>
  );
}
