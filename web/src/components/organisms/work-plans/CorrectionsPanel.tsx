import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextAreaField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import {
  CORRECTION_STATUS,
  correctionActions,
  useCorrectionInbox,
  useDecideCorrection,
  type Correction,
  type CorrectionDecision,
} from "@/services/dailyPlanService";

/** PM memutuskan permintaan koreksi laporan harian dan memeriksa revisi sampai diterima. */
export function CorrectionsPanel({ canDecide }: { canDecide: boolean }) {
  const inbox = useCorrectionInbox();
  const [target, setTarget] = useState<{ correction: Correction; decision: CorrectionDecision; label: string; force: boolean } | null>(null);
  // F9: penerimaan ditolak server karena foto wajib pekerjaan belum lengkap (409 PHOTOS_INCOMPLETE).
  const [photoGap, setPhotoGap] = useState<{ correction: Correction; message: string } | null>(null);
  const decide = useDecideCorrection();
  const items = (inbox.data ?? []).filter((c) => c.status !== "ACCEPTED" && c.status !== "REJECTED");
  if (!items.length) return null;

  const run = async (c: Correction, decision: CorrectionDecision, note?: string, force = false) => {
    try {
      await decide.mutateAsync({ id: c.correction_id, decision, note, force });
      toast.success("Keputusan disimpan.");
      setTarget(null);
      setPhotoGap(null);
    } catch (err) {
      if (err instanceof ApiError && err.code === "PHOTOS_INCOMPLETE" && decision === "ACCEPT" && !force) {
        setPhotoGap({ correction: c, message: err.message });
        return;
      }
      toast.error(errorMessage(err));
    }
  };

  return (
    <section aria-label="Koreksi laporan harian" className="mt-6 flex flex-col gap-2 rounded-panel border border-line bg-surface p-4 shadow-card">
      <TextBlock as="h2" className="text-sm font-semibold">Koreksi laporan harian ({items.length})</TextBlock>
      {items.map((c) => (
        <div key={c.correction_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <div>
            <TextBlock as="strong" className="font-medium">{c.site_name} · {c.team_name} · {c.work_date}</TextBlock>
            <TextBlock className="text-mist">
              {CORRECTION_STATUS[c.status]} — {c.requested_by_name}: {c.reason}
              {c.review_note ? ` (catatan: ${c.review_note})` : ""}
            </TextBlock>
          </div>
          {canDecide && (
            <div className="flex gap-2">
              {correctionActions(c.status).map((a) => (
                <ActionButton
                  key={a.decision}
                  size="sm"
                  variant={a.needsNote ? "outline" : "default"}
                  disabled={decide.isPending}
                  onClick={() => {
                    setPhotoGap(null);
                    if (a.needsNote) setTarget({ correction: c, decision: a.decision, label: a.label, force: false });
                    else run(c, a.decision);
                  }}
                >
                  {a.label}
                </ActionButton>
              ))}
            </div>
          )}
          {canDecide && photoGap?.correction.correction_id === c.correction_id && (
            <div role="alert" className="flex w-full flex-col gap-2 rounded-panel border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              <TextBlock>{photoGap.message}</TextBlock>
              <div className="flex flex-wrap gap-2">
                <ActionButton size="sm" variant="outline" disabled={decide.isPending} onClick={() => setPhotoGap(null)}>
                  Batal
                </ActionButton>
                <ActionButton
                  size="sm"
                  variant="outline"
                  disabled={decide.isPending}
                  onClick={() => setTarget({ correction: c, decision: "ACCEPT", label: "Terima tetap dengan catatan", force: true })}
                >
                  Terima tetap dengan catatan
                </ActionButton>
              </div>
            </div>
          )}
        </div>
      ))}
      {target && (
        <NoteDialog
          label={target.label}
          submitting={decide.isPending}
          onClose={() => setTarget(null)}
          onSubmit={(note) => run(target.correction, target.decision, note, target.force)}
        />
      )}
    </section>
  );
}

function NoteDialog({ label, submitting, onClose, onSubmit }: {
  label: string;
  submitting: boolean;
  onClose: () => void;
  onSubmit: (note: string) => void;
}) {
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const submit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!note.trim()) {
      setError("Catatan wajib diisi.");
      return;
    }
    onSubmit(note.trim());
  };
  return (
    <VmsDialog
      open
      title={label}
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={submitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="correction-note-form" disabled={submitting}>
            {submitting ? "Menyimpan..." : label}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="correction-note-form" onSubmit={submit} noValidate>
        <FormErrorText message={error} />
        <TextAreaField label="Catatan untuk ketua tim" value={note} onChange={(e) => setNote(e.target.value)} />
      </FormBlock>
    </VmsDialog>
  );
}
