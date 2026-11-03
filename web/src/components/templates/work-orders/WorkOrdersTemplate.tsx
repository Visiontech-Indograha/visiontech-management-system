import { PageTemplate } from "@/components/templates/PageTemplate";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { Plus } from "@/components/molecules/Glyphs";
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
      title="Manajemen Tugas Klien (Work Orders)"
      description="Alur kerja terpadu: Permintaan Masuk → Penugasan Survei → Review Hasil → Eksekusi Lapangan → BAST Resmi."
      action={
        <ActionButton type="button" variant="default" onClick={onOpenCreate}>
          <Plus className="h-4 w-4 mr-1.5" />
          <TextBlock as="span">Buat Work Order Baru</TextBlock>
        </ActionButton>
      }
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
