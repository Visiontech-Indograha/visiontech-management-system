import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { accuracyText, reviewReasonInfo } from "@/lib/reviewReasons";
import { pendingCheckInNote } from "@/lib/attendanceMessages";

interface Props {
  rec: {
    status: string;
    check_out_at?: string | null;
    face_status?: string | null;
    review_reasons?: string[];
    location_accuracy_m?: number | null;
  };
  onEnroll: () => void;
}

/** Banner menetap di kartu absen: akurasi lokasi, lalu alasan "perlu ditinjau" dan satu langkah perbaikan. */
export function ReviewReasonsNote({ rec, onEnroll }: Props) {
  const acc = accuracyText(rec.location_accuracy_m);
  const pending = !rec.check_out_at && rec.status === "NEEDS_REVIEW";
  const reasons = pending ? [...new Set(rec.review_reasons ?? [])] : [];
  return (
    <div className="space-y-2">
      {acc && <TextBlock className="text-sm text-mist">{acc}</TextBlock>}
      {pending && (
        <div role="status" className="space-y-2 rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
          {reasons.length === 0 ? (
            <TextBlock>{pendingCheckInNote(rec)}</TextBlock>
          ) : (
            <>
              <TextBlock className="font-semibold">Absen masuk Anda perlu ditinjau:</TextBlock>
              {reasons.map((code) => {
                const info = reviewReasonInfo(code);
                return (
                  <div key={code} className="space-y-1">
                    <TextBlock>{info.text}</TextBlock>
                    {info.action === "ENROLL" && (
                      <ActionButton variant="outline" className="h-11" onClick={onEnroll}>
                        Daftar wajah
                      </ActionButton>
                    )}
                  </div>
                );
              })}
              <TextBlock>Absen pulang bisa dilakukan setelah absen masuk disetujui.</TextBlock>
            </>
          )}
        </div>
      )}
    </div>
  );
}
