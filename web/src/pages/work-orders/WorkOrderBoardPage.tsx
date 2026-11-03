import { useState } from "react";
import { WorkOrdersTemplate } from "@/components/templates/work-orders/WorkOrdersTemplate";
import { useWorkOrders, type WorkOrder } from "@/services/workOrderService";
import { useDivisions } from "@/services/employeeService";

export function WorkOrderBoardPage() {
  const [selectedDivisionId, setSelectedDivisionId] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [assignTargetWo, setAssignTargetWo] = useState<WorkOrder | null>(null);
  const [reviewWoId, setReviewWoId] = useState<string | null>(null);
  const [bastTargetWo, setBastTargetWo] = useState<WorkOrder | null>(null);

  const { data: divisions = [] } = useDivisions();
  const {
    data: workOrders = [],
    isLoading,
    isError,
    refetch,
  } = useWorkOrders({
    division_id: selectedDivisionId || undefined,
    q: searchQuery.trim() || undefined,
  });

  return (
    <WorkOrdersTemplate
      workOrders={workOrders}
      isLoading={isLoading}
      isError={isError}
      onRetry={() => void refetch()}
      divisions={divisions}
      selectedDivisionId={selectedDivisionId}
      onDivisionChange={setSelectedDivisionId}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
      isCreateOpen={isCreateOpen}
      onOpenCreate={() => setIsCreateOpen(true)}
      onCloseCreate={() => setIsCreateOpen(false)}
      assignTargetWo={assignTargetWo}
      onAssignSurvey={setAssignTargetWo}
      onCloseAssign={() => setAssignTargetWo(null)}
      reviewWoId={reviewWoId}
      onReviewSurvey={setReviewWoId}
      onCloseReview={() => setReviewWoId(null)}
      bastTargetWo={bastTargetWo}
      onSignBast={setBastTargetWo}
      onCloseBast={() => setBastTargetWo(null)}
    />
  );
}
