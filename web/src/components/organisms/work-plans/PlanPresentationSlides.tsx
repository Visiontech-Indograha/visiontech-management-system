import type { ReactNode } from "react";
import logo from "@/assets/brand/logo-visiontech.png";
import { FilePreview } from "@/components/molecules/FilePreview";
import { formatDate, formatDateTime } from "@/lib/format";
import { INCIDENT_CATEGORY, INCIDENT_SEVERITY, type Incident } from "@/services/incidentService";
import type { FinalReport, PlanAsset, TeamMember } from "@/services/reportService";
import type { WorkPlan } from "@/services/workPlanService";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ImageView } from "@/components/molecules/ImageView";
import { PrintStyle } from "@/components/molecules/PrintStyle";

/** Satu slide: setinggi layar saat ditampilkan, satu halaman lanskap saat dicetak. */
function Slide({ title, index, total, children }: { title?: string; index: number; total: number; children: ReactNode }) {
  return (
    <section
      aria-label={title ?? "Sampul"}
      className="relative flex min-h-dvh snap-start flex-col justify-center bg-surface px-6 py-16 md:px-16 print:min-h-0 print:h-[100vh] print:break-after-page"
    >
      <ImageView src={logo} alt="Visiontech" className="absolute left-6 top-6 h-8 md:left-16 md:top-10 md:h-10" />
      <div className="mx-auto w-full max-w-4xl">
        {title && <TextBlock as="h2" className="mb-6 border-b-2 border-gold pb-3 text-2xl font-semibold text-ink md:text-4xl">{title}</TextBlock>}
        {children}
      </div>
      <TextBlock className="absolute bottom-5 right-6 text-sm text-mist md:right-16">
        {index} / {total}
      </TextBlock>
    </section>
  );
}

/**
 * Slide laporan penyelesaian (M5, prototype/js/workplans.js `presentation`):
 * sampul → tim & aset → hasil → insiden (bila ada) → lampiran → pengesahan. Cetak = lanskap satu slide per halaman.
 */
export function PlanPresentationSlides({ plan: p, report: r, team, incidents, assets }: {
  plan: WorkPlan;
  report: FinalReport;
  team: TeamMember[] | undefined;
  incidents: Incident[] | undefined;
  assets: PlanAsset[] | undefined;
}) {
  const leader = team?.find((m) => m.role_in_plan === "LEADER");
  const members = team?.filter((m) => m.role_in_plan === "MEMBER") ?? [];
  const list = incidents ?? [];
  const slides: { title?: string; body: ReactNode }[] = [
    {
      body: (
        <div className="text-center">
          <TextBlock className="mb-3 text-sm font-semibold uppercase tracking-widest text-brand-700">Laporan penyelesaian pekerjaan</TextBlock>
          <TextBlock as="h1" className="mb-8 text-3xl font-bold text-ink md:text-5xl">{p.title}</TextBlock>
          <ListBlock as="dl" className="mx-auto grid max-w-lg gap-2 text-left text-lg md:text-xl">
            <div className="flex justify-between gap-6"><TextBlock as="dt" className="text-mist">Nomor</TextBlock><TextBlock as="dd" className="font-medium">{p.number}</TextBlock></div>
            <div className="flex justify-between gap-6"><TextBlock as="dt" className="text-mist">Lokasi</TextBlock><TextBlock as="dd" className="font-medium">{p.location_text}</TextBlock></div>
            <div className="flex justify-between gap-6">
              <TextBlock as="dt" className="text-mist">Periode</TextBlock>
              <TextBlock as="dd" className="font-medium">{formatDate(p.period_start)} – {formatDate(p.period_end)}</TextBlock>
            </div>
          </ListBlock>
        </div>
      ),
    },
    {
      title: "Tim & aset",
      body: (
        <div className="grid gap-8 md:grid-cols-2">
          <div>
            <TextBlock className="mb-3 font-semibold text-brand-700">Personel</TextBlock>
            <ListBlock className="space-y-2 text-lg md:text-xl">
              <ListEntry><TextBlock as="span" className="text-mist">Ketua:</TextBlock> <TextBlock as="strong">{leader?.full_name ?? "-"}</TextBlock></ListEntry>
              <ListEntry>
                <TextBlock as="span" className="text-mist">Anggota:</TextBlock>{" "}
                {members.length ? members.map((m) => m.full_name).join(", ") : "-"}
              </ListEntry>
            </ListBlock>
          </div>
          <div>
            <TextBlock className="mb-3 font-semibold text-brand-700">Aset yang digunakan</TextBlock>
            <ListBlock className="space-y-2 text-lg md:text-xl">
              {(assets ?? []).map((a) => (
                <ListEntry key={`${a.id}-${a.allocated_at}`}>
                  {a.name} ({a.code})
                  {a.driver_name && <TextBlock as="span" className="text-mist"> · pengemudi {a.driver_name}</TextBlock>}
                  {a.returned_condition && <TextBlock as="span" className="text-mist"> · dikembalikan {a.returned_condition}</TextBlock>}
                </ListEntry>
              ))}
              {!assets?.length && <ListEntry className="text-mist">Tidak ada aset.</ListEntry>}
            </ListBlock>
          </div>
        </div>
      ),
    },
    {
      title: "Hasil pelaksanaan",
      body: (
        <div className="space-y-8 text-lg md:text-xl">
          <div>
            <TextBlock className="mb-2 font-semibold text-brand-700">Ringkasan laporan</TextBlock>
            <TextBlock className="whitespace-pre-line">{r.body}</TextBlock>
          </div>
          <div>
            <TextBlock className="mb-2 font-semibold text-brand-700">Kendala yang dihadapi</TextBlock>
            <TextBlock className="whitespace-pre-line">{r.obstacle || "-"}</TextBlock>
          </div>
        </div>
      ),
    },
    ...(list.length
      ? [
          {
            title: "Insiden / K3",
            body: (
              <ListBlock className="space-y-4 text-lg md:text-xl">
                {list.map((i) => (
                  <ListEntry key={i.id}>
                    <TextBlock as="strong">
                      [{INCIDENT_CATEGORY[i.category] ?? i.category}] {INCIDENT_SEVERITY[i.severity] ?? i.severity}
                    </TextBlock>{" "}
                    — {i.description}
                    <TextBlock as="span" className="block text-base text-mist">
                      {formatDate(i.occurred_on)} · {i.status === "RESOLVED" ? "Selesai ditangani" : "Belum selesai"}
                    </TextBlock>
                  </ListEntry>
                ))}
              </ListBlock>
            ),
          },
        ]
      : []),
    {
      title: "Lampiran pendukung",
      body: r.evidence_file_ids.length ? (
        <div className="flex flex-wrap gap-3">
          {r.evidence_file_ids.map((fid, i) => (
            <FilePreview key={fid} fileId={fid} fileName={`Lampiran ${i + 1}`} />
          ))}
        </div>
      ) : (
        <TextBlock className="text-lg text-mist">Tidak ada lampiran.</TextBlock>
      ),
    },
    {
      title: "Pengesahan",
      body: (
        <div>
          <TextBlock className="mb-12 text-center text-lg">Pekerjaan telah diselesaikan dan ditutup secara resmi.</TextBlock>
          <div className="grid gap-10 text-center md:grid-cols-2">
            <div>
              <TextBlock className="mb-10 text-mist">Ketua tim pelaksana</TextBlock>
              <TextBlock className="text-xl font-bold underline">{r.submitted_by_name ?? leader?.full_name ?? "-"}</TextBlock>
              <TextBlock className="mt-1 text-sm text-mist">{r.submitted_at ? formatDateTime(r.submitted_at) : ""}</TextBlock>
            </div>
            <div>
              <TextBlock className="mb-10 text-mist">Pemeriksa penyelesaian</TextBlock>
              <TextBlock className="text-xl font-bold underline">{r.reviewed_by_name ?? "-"}</TextBlock>
              <TextBlock className="mt-1 text-sm text-mist">{r.reviewed_at ? formatDateTime(r.reviewed_at) : ""}</TextBlock>
            </div>
          </div>
        </div>
      ),
    },
  ];
  return (
    <>
      {slides.map((s, i) => (
        <Slide key={s.title ?? "sampul"} title={s.title} index={i + 1} total={slides.length}>
          {s.body}
        </Slide>
      ))}
      <PrintStyle css="@page { size: landscape; margin: 0; }" />
    </>
  );
}
