import { AUDIT_FILTER_ENTITIES } from "@/lib/auditLabels";
import { ControlOption, ControlSelect } from "@/components/molecules/FormBlock";

/** Saring audit log per entitas (tabel yang diaudit). */
export function AuditEntityFilter({ entity, onEntityChange }: { entity: string; onEntityChange: (entity: string) => void }) {
  return (
      <ControlSelect
        aria-label="Filter entitas"
        className="h-10 w-full rounded-control border border-line bg-surface px-3 text-sm md:w-auto"
        value={entity}
        onChange={(e) => onEntityChange(e.target.value)}
      >
        <ControlOption value="">Semua entitas</ControlOption>
        {Object.entries(AUDIT_FILTER_ENTITIES).map(([value, label]) => (
          <ControlOption key={value} value={value}>
            {label}
          </ControlOption>
        ))}
      </ControlSelect>
  );
}
