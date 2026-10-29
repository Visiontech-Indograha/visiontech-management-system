import { Panel, PanelContent } from "@/components/molecules/Panel";
import { InlineLink } from "@/components/molecules/Links";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import type { HomeSummary } from "@/services/homeService";

const ROWS: { key: keyof HomeSummary; label: string; to: string }[] = [
  { key: "leaves_to_review", label: "Cuti menunggu keputusan", to: "/leaves" },
  { key: "attendance_to_review", label: "Absensi perlu diperiksa", to: "/attendance" },
  { key: "overtime_to_review", label: "Lembur menunggu persetujuan", to: "/overtime-recap" },
  { key: "mess_to_review", label: "Pengajuan mess menunggu", to: "/mess" },
  { key: "loan_requests_to_review", label: "Pengajuan pinjam aset menunggu", to: "/assets" },
  { key: "corrections_to_review", label: "Koreksi laporan harian menunggu", to: "/work-plans" },
  { key: "offboarding_open", label: "Offboarding berjalan", to: "/offboarding" },
  { key: "my_leaves_pending", label: "Cuti saya belum diputuskan", to: "/leaves" },
];

/** Antrean tindakan sesuai peran: hanya baris yang berisi (angka > 0) yang tampil, dengan tautan ke halamannya. */
export function HomeQueueCard({ summary, loading }: { summary: HomeSummary | undefined; loading: boolean }) {
  const rows = ROWS.filter((r) => (summary?.[r.key] ?? 0) > 0);
  return (
    <Panel>
      <PanelContent className="space-y-3 p-5">
        <TextBlock as="h2" className="text-title text-ink">
          Menunggu tindakan Anda
        </TextBlock>
        {loading ? (
          <LoadingBar className="h-6 w-full" />
        ) : rows.length === 0 ? (
          <TextBlock className="text-body-sm text-mist">Tidak ada yang menunggu. Semua beres.</TextBlock>
        ) : (
          <div className="divide-y divide-line">
            {rows.map((r) => (
              <div key={r.key}>
                <InlineLink to={r.to} className="flex items-center justify-between gap-3 py-2.5">
                  <TextBlock as="span" className="text-body-sm text-ink">
                    {r.label}
                  </TextBlock>
                  <TextBlock as="span" className="rounded-control bg-accent px-2.5 py-0.5 text-body-sm font-semibold text-lens">
                    {summary?.[r.key] as number}
                  </TextBlock>
                </InlineLink>
              </div>
            ))}
          </div>
        )}
      </PanelContent>
    </Panel>
  );
}
