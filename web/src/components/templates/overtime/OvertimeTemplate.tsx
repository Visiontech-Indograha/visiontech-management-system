import type { UseQueryResult } from "@tanstack/react-query";
import { OvertimeApplyButton } from "@/components/organisms/overtime/OvertimeApplyButton";
import { OvertimeApplyDialog } from "@/components/organisms/overtime/OvertimeApplyDialog";
import { OvertimeList } from "@/components/organisms/overtime/OvertimeList";
import { OvertimeReviewList } from "@/components/organisms/monitoring/OvertimeReviewList";
import type { KeysetMore } from "@/hooks/useKeysetList";
import type { Overtime } from "@/services/overtimeService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Lembur": ajukan, daftar sendiri, dan (bila berhak) antrean keputusan. */
export function OvertimeTemplate({ mine, moreMine, pending, morePending, canReview, canApply, applying, onApply, onCloseApply }: {
  mine: UseQueryResult<Overtime[]>;
  moreMine: KeysetMore;
  pending: UseQueryResult<Overtime[]>;
  morePending: KeysetMore;
  canReview: boolean;
  canApply: boolean;
  applying: boolean;
  onApply: () => void;
  onCloseApply: () => void;
}) {
  return (
    <PageTemplate title="Lembur" description="Ajukan lembur dan pantau statusnya." action={canApply ? <OvertimeApplyButton onApply={onApply} /> : undefined}>
      {canReview && <OvertimeReviewList query={pending} more={morePending} />}
      <OvertimeList query={mine} more={moreMine} titled={canReview} />
      {applying && <OvertimeApplyDialog onClose={onCloseApply} />}
    </PageTemplate>
  );
}
