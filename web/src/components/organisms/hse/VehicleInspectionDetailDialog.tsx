import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextAreaField } from "@/components/molecules/Field";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { Pill } from "@/components/molecules/Pill";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ZoomableImage } from "@/components/molecules/ZoomableImage";
import { useFileUrl } from "@/hooks/useFileUrl";
import { errorMessage } from "@/lib/errors";
import { formatDate, formatDateTime } from "@/lib/format";
import { answerLabel, inspectionStatusLabel, inspectionStatusTone, periodLabel } from "@/lib/inspectionLabels";
import { INSPECTION_MAX_NOTES, rejectReasonSchema } from "@/schemas/inspectionSchemas";
import { useChecklistTemplate, useInspection, useVerifyInspection } from "@/services/inspectionService";

function Photo({ fileId, index }: { fileId: string; index: number }) {
  const url = useFileUrl(fileId, "view");
  if (url.isError) return <TextBlock className="text-sm text-danger">Foto belum bisa dimuat.</TextBlock>;
  if (!url.data) return <TextBlock className="text-sm text-mist">Memuat foto...</TextBlock>;
  return <ZoomableImage src={url.data} alt={`Foto bukti ${index + 1}`} className="h-72 w-full" />;
}

const kmText = (km?: number | null) => (km == null ? "" : ` Kilometer: ${km}.`);
const verifiedText = (name?: string | null, at?: string | null) => (at ? ` Diperiksa ${name ?? "HSE"} pada ${formatDateTime(at)}.` : "");

function Photos({ ids }: { ids: string[] }) {
  const [idx, setIdx] = useState(0);
  if (ids.length === 0) return <TextBlock className="text-sm text-mist">Tidak ada foto bukti.</TextBlock>;
  return (
    <div className="space-y-2">
      <Photo key={ids[idx]} fileId={ids[idx]} index={idx} />
      <div className="flex flex-wrap gap-2">
        {ids.map((f, i) => (
          <ActionButton key={f} size="sm" variant={i === idx ? "default" : "outline"} onClick={() => setIdx(i)} aria-label={`Lihat foto ${i + 1} dari ${ids.length}`}>{i + 1}</ActionButton>
        ))}
      </div>
    </div>
  );
}

/** Tombol Verifikasi/Tolak; alasan wajib saat tolak. */
function VerifyBar({ id, onClose }: { id: string; onClose: () => void }) {
  const verify = useVerifyInspection();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | undefined>();
  const run = (status: "VERIFIED" | "REJECTED", notes?: string) =>
    verify.mutate({ id, status, notes }, {
      onSuccess: () => { toast.success(status === "VERIFIED" ? "Inspeksi diverifikasi." : "Inspeksi ditolak."); onClose(); },
      onError: (err) => toast.error(errorMessage(err, "Belum bisa menyimpan. Coba lagi.")),
    });
  const onReject = () => {
    const r = rejectReasonSchema.safeParse(reason);
    if (!r.success) return setReasonError(r.error.issues[0]?.message);
    setReasonError(undefined);
    run("REJECTED", r.data);
  };
  if (!rejecting)
    return (
      <div className="flex justify-end gap-2">
        <ActionButton variant="outline" onClick={() => setRejecting(true)}>Tolak</ActionButton>
        <ActionButton pending={verify.isPending} onClick={() => run("VERIFIED")}>Verifikasi</ActionButton>
      </div>
    );
  return (
    <div>
      <TextAreaField label="Alasan penolakan" maxLength={INSPECTION_MAX_NOTES} value={reason} error={reasonError} onChange={(e) => setReason(e.target.value)} />
      <div className="flex justify-end gap-2">
        <ActionButton variant="outline" onClick={() => setRejecting(false)}>Batal</ActionButton>
        <ActionButton variant="destructive" pending={verify.isPending} onClick={onReject}>Tolak inspeksi</ActionButton>
      </div>
    </div>
  );
}

/** Detail inspeksi: daftar periksa, foto bukti (bisa diperbesar), status, dan Verifikasi/Tolak bagi pemegang izin kelola. */
export function VehicleInspectionDetailDialog({ id, canVerify, onClose }: { id: string; canVerify: boolean; onClose: () => void }) {
  const query = useInspection(id);
  const template = useChecklistTemplate();
  const d = query.data;
  const labels = new Map((template.data?.items ?? []).map((i) => [i.key, i.label]));
  return (
    <VmsDialog open title="Detail inspeksi kendaraan" onClose={onClose} size="md">
      <QueryState query={query} errorText="Detail inspeksi belum bisa dimuat. Coba lagi.">
        {d && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <TextBlock className="font-semibold text-ink">{d.number_plate ?? "-"} - {d.vehicle_name ?? "-"}</TextBlock>
              <Pill tone={inspectionStatusTone(d.status)}>{inspectionStatusLabel(d.status)}</Pill>
            </div>
            <TextBlock className="text-sm text-mist">
              {periodLabel(d.period_type)}, {formatDate(d.inspection_date)}. Pemeriksa: {d.inspector_name ?? "-"}.
              {kmText(d.odometer_km)}{verifiedText(d.verifier_name, d.verified_at)}
            </TextBlock>
            <ListBlock className="divide-y divide-line rounded-panel border border-line">
              {Object.entries(d.checklist_json).map(([k, v]) => (
                <ListEntry key={k} className="flex items-center justify-between gap-3 p-3 text-sm">
                  <TextBlock as="span">{labels.get(k) ?? k}</TextBlock>
                  <TextBlock as="span" className="font-medium text-ink">{answerLabel(v)}</TextBlock>
                </ListEntry>
              ))}
            </ListBlock>
            {d.notes && <TextBlock className="text-sm text-ink">Catatan: {d.notes}</TextBlock>}
            <Photos ids={d.photos_json} />
            {canVerify && d.status === "SUBMITTED" && <VerifyBar id={id} onClose={onClose} />}
          </div>
        )}
      </QueryState>
    </VmsDialog>
  );
}
