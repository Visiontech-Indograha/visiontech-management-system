import type { UseQueryResult } from "@tanstack/react-query";
import { WorkCompletionNavTabs } from "@/components/organisms/work-completions/WorkCompletionNavTabs";
import { ProjectAddButton } from "@/components/organisms/projects/ProjectAddButton";
import { ProjectFormDialog } from "@/components/organisms/projects/ProjectFormDialog";
import { ProjectDeleteDialog } from "@/components/organisms/projects/ProjectDeleteDialog";
import { ProjectList } from "@/components/organisms/projects/ProjectList";
import type { Project, ProjectFilter } from "@/services/projectService";
import type { Client } from "@/services/clientService";
import type { Division } from "@/services/employeeService";
import { PageTemplate } from "../PageTemplate";

export function ProjectsTemplate({
  projects,
  clients,
  divisions,
  filter,
  onFilterChange,
  canManage,
  editing,
  deleting,
  onAdd,
  onEdit,
  onDelete,
  onCloseEdit,
  onCloseDelete,
}: {
  projects: UseQueryResult<Project[]>;
  clients: Client[] | undefined;
  divisions: Division[] | undefined;
  filter: ProjectFilter;
  onFilterChange: (update: Partial<ProjectFilter>) => void;
  canManage: boolean;
  editing: Project | "new" | null;
  deleting: Project | null;
  onAdd: () => void;
  onEdit: (project: Project) => void;
  onDelete: (project: Project) => void;
  onCloseEdit: () => void;
  onCloseDelete: () => void;
}) {
  return (
    <PageTemplate
      title="Master Proyek (SPK)"
      description="Kelola seluruh kontrak kerja induk (SPK), target deliverable, rentang waktu, dan pembagian tugas divisi."
      action={canManage && <ProjectAddButton onAdd={onAdd} />}
    >
      <WorkCompletionNavTabs activeTab="projects" />
      <ProjectList
        projects={projects}
        clients={clients}
        divisions={divisions}
        filter={filter}
        onFilterChange={onFilterChange}
        canManage={canManage}
        onAdd={onAdd}
        onEdit={onEdit}
        onDelete={onDelete}
      />
      {editing && (
        <ProjectFormDialog
          project={editing === "new" ? null : editing}
          onClose={onCloseEdit}
        />
      )}
      {deleting && (
        <ProjectDeleteDialog project={deleting} onClose={onCloseDelete} />
      )}
    </PageTemplate>
  );
}
