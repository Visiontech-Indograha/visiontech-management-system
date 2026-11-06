import { PageTemplate } from "@/components/templates/PageTemplate";
import { WorkOrderCreateAction } from "@/components/organisms/work-orders/WorkOrderCreateAction";
import { WorkOrderList } from "@/components/organisms/work-orders/WorkOrderList";
import { WorkOrderCreateModal } from "@/components/organisms/work-orders/WorkOrderCreateModal";
import { WorkOrderAssignModal } from "@/components/organisms/work-orders/WorkOrderAssignModal";
import { WorkOrderSurveyReviewModal } from "@/components/organisms/work-orders/WorkOrderSurveyReviewModal";
import { WorkOrderBastModal } from "@/components/organisms/work-orders/WorkOrderBastModal";
import type { WorkOrder } from "@/services/workOrderService";

interface WorkOrdersTemplateProps {
  workOrders: WorkOrder[];
  isLoading: boolean;
  isError?: boolean;
  onRetry?: () => void;
  divisions: Array<{ id: string; name: string }>;
  selectedDivisionId: string;
  onDivisionChange: (id: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  isCreateOpen: boolean;
  onOpenCreate: () => void;
  onCloseCreate: () => void;
  assignTargetWo: WorkOrder | null;
  onAssignSurvey: (wo: WorkOrder) => void;
  onCloseAssign: () => void;
  reviewWoId: string | null;
  onReviewSurvey: (woId: string) => void;
  onCloseReview: () => void;
  bastTargetWo: WorkOrder | null;
  onSignBast: (wo: WorkOrder) => void;
  onCloseBast: () => void;
}

export function WorkOrdersTemplate({
  workOrders,
  isLoading,
  isError = false,
  onRetry,
  divisions,
  selectedDivisionId,
  onDivisionChange,
  searchQuery,
  onSearchChange,
  isCreateOpen,
  onOpenCreate,
  onCloseCreate,
  assignTargetWo,
  onAssignSurvey,
  onCloseAssign,
  reviewWoId,
  onReviewSurvey,
  onCloseReview,
  bastTargetWo,
  onSignBast,
  onCloseBast,
}: WorkOrdersTemplateProps) {
  return (
    <PageTemplate
      title="Tugas Klien"
      description="Alur tugas: permintaan masuk → survei lapangan → cek hasil survei → pengerjaan di lapangan → surat serah terima resmi."
      action={<WorkOrderCreateAction onClick={onOpenCreate} />}
    >
      <WorkOrderList
        workOrders={workOrders}
        isLoading={isLoading}
        isError={isError}
        onRetry={onRetry}
        divisions={divisions}
        selectedDivisionId={selectedDivisionId}
        onDivisionChange={onDivisionChange}
        searchQuery={searchQuery}
        onSearchChange={onSearchChange}
        onAssignSurvey={onAssignSurvey}
        onReviewSurvey={onReviewSurvey}
        onSignBast={onSignBast}
      />

      <WorkOrderCreateModal
        isOpen={isCreateOpen}
        onClose={onCloseCreate}
        defaultDivisionId={selectedDivisionId}
      />

      <WorkOrderAssignModal
        key={assignTargetWo?.work_order_id ?? "assign-empty"}
        workOrder={assignTargetWo}
        onClose={onCloseAssign}
      />

      <WorkOrderSurveyReviewModal
        key={reviewWoId ?? "review-empty"}
        workOrderId={reviewWoId}
        onClose={onCloseReview}
      />

      <WorkOrderBastModal
        key={bastTargetWo?.work_order_id ?? "bast-empty"}
        workOrder={bastTargetWo}
        onClose={onCloseBast}
      />
    </PageTemplate>
  );
}
