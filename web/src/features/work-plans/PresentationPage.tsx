import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import logo from "@/assets/brand/logo-visiontech.png";
import { FilePreview } from "@/components/molecules/FilePreview";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, formatDateTime } from "@/lib/format";
import { useWorkPlan } from "./api";
import { INCIDENT_CATEGORY, INCIDENT_SEVERITY, useSessionIncidents } from "./incidents-api";
import { useFinalReport, usePlanTeam } from "./report-api";

/** Satu slide: setinggi layar saat ditampilkan, satu halaman lanskap saat dicetak. */
function Slide({ title, index, total, children }: { title?: string; index: number; total: number; children: ReactNode }) {
  return (
    <section
      aria-label={title ?? "Sampul"}
      className="relative flex min-h-dvh snap-start flex-col justify-center bg-surface px-6 py-16 md:px-16 print:min-h-0 print:h-[100vh] print:break-after-page"
    >
      <img src={logo} alt="Visiontech" className="absolute left-6 top-6 h-8 md:left-16 md:top-10 md:h-10" />
      <div className="mx-auto w-full max-w-4xl">
        {title && <h2 className="mb-6 border-b-2 border-gold pb-3 text-2xl font-semibold text-ink md:text-4xl">{title}</h2>}
        {children}
      </div>
      <p className="absolute bottom-5 right-6 text-sm text-mist md:right-16">
        {index} / {total}
      </p>
    </section>
  );
}

/**
 * Mode presentasi laporan (M5, prototype/js/workplans.js `presentation`): hanya untuk SK yang sudah
 * selesai. Sampul → tim → hasil → insiden → lampiran → pengesahan. "Simpan PDF" memakai cetak peramban
 * (lanskap). Layar penuh, di luar AppShell.
 */
export function PresentationPage() {
  const { id = "" } = useParams();
  const plan = useWorkPlan(id);
  const completed = plan.data?.status === "COMPLETED";
  const team = usePlanTeam(id);
  const report = useFinalReport(id, completed);
  const incidents = useSessionIncidents(id);
  const p = plan.data;
  const r = report.data;

  if (plan.isPending || (completed && (team.isPending || report.isPending || incidents.isPending)))
    return (
      <main className="mx-auto max-w-4xl space-y-4 p-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-64 w-full" />
      </main>
    );
  if (!p || !completed || !r)
    return (
      <main className="mx-auto max-w-xl p-6 text-center">
        <h1 className="mb-2 text-xl font-semibold">Presentasi tidak tersedia</h1>
        <p className="mb-6 text-mist">Hanya pekerjaan yang sudah selesai yang dapat dipresentasikan.</p>
        <Link to={p ? `/work-plans/${p.id}` : "/work-plans"} className="font-semibold text-lens hover:underline">
          Kembali
        </Link>
      </main>
    );

  const leader = team.data?.find((m) => m.role_in_plan === "LEADER");
  const members = team.data?.filter((m) => m.role_in_plan === "MEMBER") ?? [];
  const list = incidents.data ?? [];
  const slides: { title?: string; body: ReactNode }[] = [
    {
      body: (
        <div className="text-center">
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-brand-700">Laporan penyelesaian pekerjaan</p>
          <h1 className="mb-8 text-3xl font-bold text-ink md:text-5xl">{p.title}</h1>
          <dl className="mx-auto grid max-w-lg gap-2 text-left text-lg md:text-xl">
            <div className="flex justify-between gap-6"><dt className="text-mist">Nomor</dt><dd className="font-medium">{p.number}</dd></div>
            <div className="flex justify-between gap-6"><dt className="text-mist">Lokasi</dt><dd className="font-medium">{p.location_text}</dd></div>
            <div className="flex justify-between gap-6">
              <dt className="text-mist">Periode</dt>
              <dd className="font-medium">{formatDate(p.period_start)} – {formatDate(p.period_end)}</dd>
            </div>
          </dl>
        </div>
      ),
    },
    {
      title: "Tim",
      body: (
        <ul className="space-y-3 text-lg md:text-2xl">
          <li><span className="text-mist">Ketua:</span> <strong>{leader?.full_name ?? "-"}</strong></li>
          <li>
            <span className="text-mist">Anggota:</span>{" "}
            {members.length ? members.map((m) => m.full_name).join(", ") : "-"}
          </li>
        </ul>
      ),
    },
    {
      title: "Hasil pelaksanaan",
      body: (
        <div className="space-y-8 text-lg md:text-xl">
          <div>
            <p className="mb-2 font-semibold text-brand-700">Ringkasan laporan</p>
            <p className="whitespace-pre-line">{r.body}</p>
          </div>
          <div>
            <p className="mb-2 font-semibold text-brand-700">Kendala yang dihadapi</p>
            <p className="whitespace-pre-line">{r.obstacle || "-"}</p>
          </div>
        </div>
      ),
    },
    ...(list.length
      ? [
          {
            title: "Insiden / K3",
            body: (
              <ul className="space-y-4 text-lg md:text-xl">
                {list.map((i) => (
                  <li key={i.id}>
                    <strong>
                      [{INCIDENT_CATEGORY[i.category] ?? i.category}] {INCIDENT_SEVERITY[i.severity] ?? i.severity}
                    </strong>{" "}
                    — {i.description}
                    <span className="block text-base text-mist">
                      {formatDate(i.occurred_on)} · {i.status === "RESOLVED" ? "Selesai ditangani" : "Belum selesai"}
                    </span>
                  </li>
                ))}
              </ul>
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
        <p className="text-lg text-mist">Tidak ada lampiran.</p>
      ),
    },
    {
      title: "Pengesahan",
      body: (
        <div>
          <p className="mb-12 text-center text-lg">Pekerjaan telah diselesaikan dan ditutup secara resmi.</p>
          <div className="grid gap-10 text-center md:grid-cols-2">
            <div>
              <p className="mb-10 text-mist">Ketua tim pelaksana</p>
              <p className="text-xl font-bold underline">{r.submitted_by_name ?? leader?.full_name ?? "-"}</p>
              <p className="mt-1 text-sm text-mist">{r.submitted_at ? formatDateTime(r.submitted_at) : ""}</p>
            </div>
            <div>
              <p className="mb-10 text-mist">Pemeriksa penyelesaian</p>
              <p className="text-xl font-bold underline">{r.reviewed_by_name ?? "-"}</p>
              <p className="mt-1 text-sm text-mist">{r.reviewed_at ? formatDateTime(r.reviewed_at) : ""}</p>
            </div>
          </div>
        </div>
      ),
    },
  ];

  return (
    <main className="h-dvh snap-y snap-mandatory overflow-y-auto bg-ink/5 print:h-auto print:overflow-visible">
      <div className="fixed bottom-4 left-1/2 z-10 flex -translate-x-1/2 gap-2 md:bottom-auto md:left-auto md:right-4 md:top-4 md:translate-x-0 print:hidden">
        <Button onClick={() => window.print()}>Simpan PDF</Button>
        <Button asChild variant="outline">
          <Link to={`/work-plans/${p.id}`}>Tutup presentasi</Link>
        </Button>
      </div>
      {slides.map((s, i) => (
        <Slide key={s.title ?? "sampul"} title={s.title} index={i + 1} total={slides.length}>
          {s.body}
        </Slide>
      ))}
      <style>{"@page { size: landscape; margin: 0; }"}</style>
    </main>
  );
}
