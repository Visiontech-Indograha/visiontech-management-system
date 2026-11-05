import type { UseQueryResult } from "@tanstack/react-query";
import { OvertimeApplyButton } from "@/components/organisms/overtime/OvertimeApplyButton";
import { OvertimeApplyDialog } from "@/components/organisms/overtime/OvertimeApplyDialog";
import { OvertimeList } from "@/components/organisms/overtime/OvertimeList";
import { OvertimeReviewList } from "@/components/organisms/monitoring/OvertimeReviewList";
import type { Overtime } from "@/services/overtimeService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Lembur": ajukan, daftar sendiri, dan (bila berhak) antrean keputusan. */
export function OvertimeTemplate({ mine, pending, canReview, applying, onApply, onCloseApply }: {
  mine: UseQueryResult<Overtime[]>;
  pending: UseQueryResult<Overtime[]>;
  canReview: boolean;
  applying: boolean;
  onApply: () => void;
  onCloseApply: () => void;
}) {
  return (
    <PageTemplate title="Lembur" description="Ajukan lembur dan pantau statusnya." action={<OvertimeApplyButton onApply={onApply} />}>
      {canReview && <OvertimeReviewList query={pending} />}
      <OvertimeList query={mine} titled={canReview} />
      {applying && <OvertimeApplyDialog onClose={onCloseApply} />}
    </PageTemplate>
  );
}
