import { useState } from "react";
import { WorkCompletionsTemplate } from "@/components/templates/work-completions/WorkCompletionsTemplate";
import { useWorkCompletions } from "@/services/workCompletionService";
import { useSession } from "@/stores/sessionStore";

export function WorkCompletionsPage() {
  const { me } = useSession();
  const canManage =
    Boolean(me?.permissions.includes("create:plan")) ||
    me?.role === "PROJECT_MANAGER" ||
    me?.role === "OPERATIONAL_MANAGER";

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const completionsQuery = useWorkCompletions();

  return (
    <WorkCompletionsTemplate
      query={completionsQuery}
      canManage={canManage}
      adding={isCreateOpen}
      onAdd={() => setIsCreateOpen(true)}
      onCloseAdd={() => setIsCreateOpen(false)}
    />
  );
}
