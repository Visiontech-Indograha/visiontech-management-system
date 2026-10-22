import { ImageView } from "@/components/molecules/ImageView";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { Pill } from "@/components/molecules/Pill";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useFileUrl } from "@/hooks/useFileUrl";
import type { Survey } from "@/services/surveyService";

type Point = Survey["points"][number];

function Photo({ fileId, slot }: { fileId: string; slot: string | null | undefined }) {
  const { data: url } = useFileUrl(fileId, "view");
  return (
    <div className="w-full max-w-[16rem]">
      <div className="aspect-[3/4] overflow-hidden rounded-control border border-line bg-hover">
        {url && <ImageView src={url} alt={slot ?? "Foto titik"} className="h-full w-full object-cover" />}
      </div>
      <TextBlock className="mt-1 text-center text-xs font-medium">{slot ?? "Foto"}</TextBlock>
    </div>
  );
}

const num = (v: string | number) => {
  const n = Number(v);
  return Number.isInteger(n) ? String(n) : String(n).replace(".", ",");
};

function PointCard({ point, index }: { point: Point; index: number }) {
  const materials = point.lines.filter((l) => l.category === "MATERIAL");
  const needs = point.lines.filter((l) => l.category === "KEBUTUHAN");
  const cables = point.lines.filter((l) => l.category === "KABEL");
  return (
    <article className="rounded-panel border border-line bg-surface p-4 shadow-card" aria-label={point.name}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <TextBlock className="font-semibold text-ink">{`${index}. ${point.name}`}</TextBlock>
        <Pill tone="neutral">{point.point_type_name}</Pill>
        <Pill tone={point.point_status === "EXISTING" ? "success" : "info"}>
          {point.point_status === "EXISTING" ? "Sudah terpasang" : "Usulan baru"}
        </Pill>
      </div>
      <div className="flex flex-wrap gap-4">
        {point.photos.map((p) => (
          <Photo key={p.file_id} fileId={p.file_id} slot={p.slot} />
        ))}
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div>
          <TextBlock className="mb-1 text-xs font-semibold uppercase text-mist">Remark</TextBlock>
          <ListBlock className="list-disc space-y-0.5 pl-5 text-sm">
            {point.remarks.length === 0 && <ListEntry className="list-none -ml-5 text-mist">-</ListEntry>}
            {point.remarks.map((r, i) => (
              <ListEntry key={i}>{r}</ListEntry>
            ))}
          </ListBlock>
          {needs.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {needs.map((n) => (
                <Pill key={n.bom_id} tone="warning">{n.name}</Pill>
              ))}
            </div>
          )}
        </div>
        <div>
          <TextBlock className="mb-1 text-xs font-semibold uppercase text-mist">Material titik</TextBlock>
          <ListBlock className="space-y-0.5 text-sm">
            {materials.length === 0 && <ListEntry className="text-mist">-</ListEntry>}
            {materials.map((m) => (
              <ListEntry key={m.bom_id}>{`${m.name} = ${num(m.qty)} ${m.unit}`}</ListEntry>
            ))}
          </ListBlock>
        </div>
        {cables.length > 0 && (
          <div>
            <TextBlock className="mb-1 text-xs font-semibold uppercase text-mist">Kabel (FO)</TextBlock>
            <ListBlock className="space-y-0.5 text-sm">
              {cables.map((c) => (
                <ListEntry key={c.bom_id}>
                  {c.notes ? `${c.name}: ${c.notes}` : `${c.name}: ${num(c.qty)} ${c.unit}`}
                </ListEntry>
              ))}
            </ListBlock>
          </div>
        )}
      </div>
    </article>
  );
}

/** Titik survei beserta foto per slot, remark, kebutuhan, material, dan kabel — sama urutannya dengan laporan. */
export function SurveyPointsPanel({ survey }: { survey: Survey }) {
  if (survey.points.length === 0)
    return <TextBlock className="text-sm text-mist">Ketua tim belum menambahkan titik.</TextBlock>;
  return (
    <div className="space-y-4">
      {survey.points.map((p, i) => (
        <PointCard key={p.point_id} point={p} index={i + 1} />
      ))}
    </div>
  );
}
