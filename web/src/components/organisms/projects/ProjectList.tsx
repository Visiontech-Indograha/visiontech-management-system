import type { UseQueryResult } from "@tanstack/react-query";
import { formatDate } from "@/lib/format";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TextField, SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { Briefcase, Building2, Calendar, CheckCircle2, Clock, MapPin, User } from "@/components/molecules/Glyphs";
import { ProjectAddButton } from "./ProjectAddButton";
import type { Project, ProjectFilter } from "@/services/projectService";
import type { Client } from "@/services/clientService";
import type { Division } from "@/services/employeeService";

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  ONGOING: { label: "Berjalan", className: "bg-lens/15 text-lens font-medium" },
  DRAFT: { label: "Persiapan", className: "bg-hover text-mist font-medium" },
  COMPLETED: { label: "Selesai", className: "bg-leaf/15 text-leaf font-medium" },
  CANCELLED: { label: "Dibatalkan", className: "bg-danger/15 text-danger font-medium" },
};

export function ProjectList({
  projects,
  clients,
  divisions,
  filter,
  onFilterChange,
  canManage,
  onAdd,
  onEdit,
  onDelete,
}: {
  projects: UseQueryResult<Project[]>;
  clients: Client[] | undefined;
  divisions: Division[] | undefined;
  filter: ProjectFilter;
  onFilterChange: (update: Partial<ProjectFilter>) => void;
  canManage: boolean;
  onAdd: () => void;
  onEdit: (project: Project) => void;
  onDelete: (project: Project) => void;
}) {
  return (
    <div className="space-y-4">
      {/* Baris Filter */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <TextField
          label=""
          placeholder="Cari SPK atau judul proyek..."
          value={filter.q ?? ""}
          onChange={(e) => onFilterChange({ q: e.target.value })}
        />

        <SelectField
          label=""
          value={filter.client_id ?? ""}
          onChange={(e) => onFilterChange({ client_id: e.target.value || undefined })}
        >
          <ControlOption value="">-- Semua Klien --</ControlOption>
          {(clients ?? []).map((c) => (
            <ControlOption key={c.client_id} value={c.client_id}>
              {c.client_code} - {c.name}
            </ControlOption>
          ))}
        </SelectField>

        <SelectField
          label=""
          value={filter.division_id ?? ""}
          onChange={(e) => onFilterChange({ division_id: e.target.value || undefined })}
        >
          <ControlOption value="">-- Semua Divisi --</ControlOption>
          {(divisions ?? []).map((d) => (
            <ControlOption key={d.id} value={d.id}>
              {d.name}
            </ControlOption>
          ))}
        </SelectField>

        <SelectField
          label=""
          value={filter.status ?? ""}
          onChange={(e) => onFilterChange({ status: e.target.value || undefined })}
        >
          <ControlOption value="">-- Semua Status --</ControlOption>
          <ControlOption value="ONGOING">Berjalan</ControlOption>
          <ControlOption value="DRAFT">Persiapan</ControlOption>
          <ControlOption value="COMPLETED">Selesai</ControlOption>
          <ControlOption value="CANCELLED">Dibatalkan</ControlOption>
        </SelectField>
      </div>

      {projects.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <LoadingBar className="h-32" />
          <LoadingBar className="h-32" />
        </div>
      )}

      {projects.isError && (
        <RetryNotice
          message="Daftar proyek tidak dapat dimuat."
          onRetry={() => projects.refetch()}
        />
      )}

      {projects.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface p-8 text-center shadow-card">
          <Briefcase className="mx-auto mb-3 text-mist" size={36} />
          <TextBlock className="mb-2 font-medium">Belum ada proyek</TextBlock>
          <TextBlock className="mb-4 text-sm text-mist">
            {filter.q || filter.client_id || filter.division_id || filter.status
              ? "Tidak ada proyek yang sesuai dengan kriteria filter."
              : "Daftarkan kontrak kerja proyek untuk membagi pekerjaan ke tim lapangan."}
          </TextBlock>
          {canManage && !filter.q && !filter.client_id && <ProjectAddButton onAdd={onAdd} />}
        </div>
      )}

      {projects.data && projects.data.length > 0 && (
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {projects.data.map((p) => {
            const statusConfig = STATUS_BADGE[p.status] ?? {
              label: p.status,
              className: "bg-hover text-mist",
            };
            return (
              <ListEntry
                key={p.project_id}
                className="flex flex-col justify-between rounded-panel border border-line bg-surface p-4 shadow-card hover:border-mist transition-colors"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <TextBlock as="span" className="rounded-control bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
                          {p.spk_number}
                        </TextBlock>
                        <TextBlock as="span" className={`rounded-control px-2 py-0.5 text-xs ${statusConfig.className}`}>
                          {statusConfig.label}
                        </TextBlock>
                      </div>
                      <TextBlock className="font-semibold text-foreground mt-1.5">{p.project_title}</TextBlock>
                    </div>
                  </div>

                  <div className="space-y-1.5 my-3 text-xs text-mist">
                    <div className="flex items-center gap-2">
                      <Building2 size={14} className="text-mist shrink-0" />
                      <TextBlock as="span">
                        Klien: <TextBlock as="strong" className="text-foreground">{p.client_name}</TextBlock>
                      </TextBlock>
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin size={14} className="text-mist shrink-0" />
                      <TextBlock as="span">{p.division_name} · {p.office_name}</TextBlock>
                    </div>
                    <div className="flex items-center gap-2">
                      <User size={14} className="text-mist shrink-0" />
                      <TextBlock as="span">
                        PM: <TextBlock as="strong" className="text-foreground">{p.pm_name}</TextBlock>
                      </TextBlock>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar size={14} className="text-mist shrink-0" />
                      <TextBlock as="span">
                        {formatDate(String(p.start_date))} s/d {formatDate(String(p.end_date))}
                      </TextBlock>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 my-2 p-2 rounded-control bg-hover text-xs">
                    <CheckCircle2 size={14} className="text-leaf shrink-0" />
                    <TextBlock as="span">
                      Target: <TextBlock as="strong" className="text-foreground font-semibold">{Number(p.total_target_qty).toLocaleString("id-ID")}</TextBlock> {p.unit_measure}
                    </TextBlock>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-line flex items-center justify-between text-xs">
                  <div className="text-mist flex items-center gap-1.5">
                    <Clock size={13} />
                    <TextBlock as="span">
                      <TextBlock as="strong">{p.daily_plan_count}</TextBlock> jadwal harian
                    </TextBlock>
                  </div>
                  {canManage && (
                    <div className="flex items-center gap-2">
                      <ActionButton
                        variant="ghost"
                        size="sm"
                        onClick={() => onEdit(p)}
                        aria-label={`Ubah ${p.project_title}`}
                      >
                        Ubah
                      </ActionButton>
                      <ActionButton
                        variant="ghost"
                        size="sm"
                        className="text-danger hover:text-danger"
                        onClick={() => onDelete(p)}
                        aria-label={`Hapus ${p.project_title}`}
                      >
                        Hapus
                      </ActionButton>
                    </div>
                  )}
                </div>
              </ListEntry>
            );
          })}
        </ListBlock>
      )}
    </div>
  );
}
