import type { UseQueryResult } from "@tanstack/react-query";
import { WorkCompletionNavTabs } from "@/components/organisms/work-completions/WorkCompletionNavTabs";
import { WorkCompletionAddButton } from "@/components/organisms/work-completions/WorkCompletionAddButton";
import { WorkCompletionFormDialog } from "@/components/organisms/work-completions/WorkCompletionFormDialog";
import { WorkCompletionList } from "@/components/organisms/work-completions/WorkCompletionList";
import type { WorkCompletionListResponse } from "@/services/workCompletionService";
import { PageTemplate } from "../PageTemplate";

export function WorkCompletionsTemplate({
  query,
  canManage,
  adding,
  onAdd,
  onCloseAdd,
}: {
  query: UseQueryResult<WorkCompletionListResponse>;
  canManage: boolean;
  adding: boolean;
  onAdd: () => void;
  onCloseAdd: () => void;
}) {
  return (
    <PageTemplate
      title="Pekerjaan klien"
      description="Pekerjaan dari klien, kemajuannya, hasil kerja, dan dokumen serah terima."
      action={canManage && <WorkCompletionAddButton onAdd={onAdd} />}
    >
      <WorkCompletionNavTabs activeTab="completions" />
      <WorkCompletionList query={query} canManage={canManage} onAdd={onAdd} />
      {adding && <WorkCompletionFormDialog onClose={onCloseAdd} />}
    </PageTemplate>
  );
}
