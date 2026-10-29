import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { DialogActions } from "@/components/molecules/DialogActions";
import { TextAreaField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { CheckCircle2, ClipboardCheck, Download, Send } from "@/components/molecules/Glyphs";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { errorMessage } from "@/lib/errors";
import { useOfficialSurveyReport, useReviewSurvey, type Survey } from "@/services/surveyService";

/** Aksi PM pada survei: setujui / kembalikan (catatan wajib), unduh laporan resmi, rencanakan pekerjaan lanjutan. */
export function SurveyReviewBar({ survey, onPlan }: { survey: Survey; onPlan: () => void }) {
  const review = useReviewSurvey(survey.task_id);
  const official = useOfficialSurveyReport(survey.task_id);
  const [returning, setReturning] = useState(false);
  const [approving, setApproving] = useState(false);
  const [note, setNote] = useState("");

  const approve = async () => {
    try {
      await review.mutateAsync({ decision: "APPROVE" });
      toast.success("Survei disetujui. Laporan resmi siap diunduh; lanjutkan dengan merencanakan pekerjaan.");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const sendBack = async () => {
    try {
      await review.mutateAsync({ decision: "RETURN", note });
      toast.success("Survei dikembalikan ke ketua tim.");
      setReturning(false);
      setNote("");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const download = async () => {
    try {
      await official.mutateAsync();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {survey.can_review && (
        <>
          <ActionButton onClick={() => setApproving(true)} disabled={review.isPending}>
            <CheckCircle2 className="mr-1.5 h-4 w-4" /> Setujui survei
          </ActionButton>
          <ActionButton variant="outline" onClick={() => setReturning(true)} disabled={review.isPending}>
            <Send className="mr-1.5 h-4 w-4" /> Kembalikan ke ketua tim
          </ActionButton>
        </>
      )}
      {survey.state !== "DRAFT" && (
        <ActionButton variant="outline" onClick={download} disabled={official.isPending}>
          <Download className="mr-1.5 h-4 w-4" /> {official.isPending ? "Menyiapkan…" : "Unduh laporan resmi (.docx)"}
        </ActionButton>
      )}
      {survey.state === "APPROVED" && (
        <ActionButton variant="outline" onClick={onPlan}>
          <ClipboardCheck className="mr-1.5 h-4 w-4" /> Rencanakan pekerjaan dari survei
        </ActionButton>
      )}
      {returning && (
        <VmsDialog
          open
          title="Kembalikan survei"
          onClose={() => setReturning(false)}
          footer={
            <DialogActions
              onCancel={() => setReturning(false)}
              busy={review.isPending}
              formId="survey-return-form"
              submitLabel="Kembalikan"
              busyLabel="Mengirim..."
            />
          }
        >
          <TextBlock className="mb-3 text-sm text-mist">
            Survei kembali bisa diubah ketua tim. Tulis apa yang perlu diperbaiki — catatan tampil di aplikasi HP.
          </TextBlock>
          <FormBlock
            id="survey-return-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (note.trim()) void sendBack();
              else toast.error("Tulis catatan perbaikan untuk ketua tim.");
            }}
          >
            <TextAreaField label="Catatan perbaikan" value={note} onChange={(e) => setNote(e.target.value)} />
          </FormBlock>
        </VmsDialog>
      )}
      <ConfirmDialog
        open={approving}
        title="Setujui survei?"
        message="Survei akan disetujui dan laporan resmi dapat diunduh. Setelah itu pekerjaan dapat direncanakan."
        confirmLabel="Setujui survei"
        busy={review.isPending}
        onConfirm={async () => {
          await approve();
          setApproving(false);
        }}
        onClose={() => setApproving(false)}
      />
    </div>
  );
}
