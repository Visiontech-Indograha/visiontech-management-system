import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ProjectsTemplate } from "@/components/templates/projects/ProjectsTemplate";
import { useProjects, type Project, type ProjectFilter } from "@/services/projectService";
import { useClients } from "@/services/clientService";
import { useUserDivisions } from "@/services/employeeService";
import { useSession } from "@/stores/sessionStore";

export function ProjectsPage() {
  const { me } = useSession();
  const canManage =
    Boolean(me?.permissions.includes("create:plan")) ||
    me?.role === "PROJECT_MANAGER" ||
    me?.role === "OPERATIONAL_MANAGER" ||
    me?.role === "SUPER_ADMIN";

  // Dari "Buat SPK untuk klien ini" (halaman Pekerjaan klien): daftar langsung disaring ke klien itu.
  const [params] = useSearchParams();
  const [filter, setFilter] = useState<ProjectFilter>({
    division_id: me?.division_id || undefined,
    client_id: params.get("client_id") || undefined,
  });
  const [editing, setEditing] = useState<Project | "new" | null>(null);
  const [deleting, setDeleting] = useState<Project | null>(null);

  const projectsQuery = useProjects(filter);
  const { data: clients } = useClients(true);
  const { data: divisions } = useUserDivisions();

  const handleFilterChange = (update: Partial<ProjectFilter>) => {
    setFilter((prev) => ({ ...prev, ...update }));
  };

  return (
    <ProjectsTemplate
      projects={projectsQuery}
      clients={clients}
      divisions={divisions}
      filter={filter}
      onFilterChange={handleFilterChange}
      canManage={canManage}
      editing={editing}
      deleting={deleting}
      onAdd={() => setEditing("new")}
      onEdit={setEditing}
      onDelete={setDeleting}
      onCloseEdit={() => setEditing(null)}
      onCloseDelete={() => setDeleting(null)}
    />
  );
}
