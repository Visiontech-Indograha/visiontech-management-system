import { AUDIT_ENTITIES } from "@/lib/auditLabels";

/** Saring audit log per entitas (tabel yang diaudit). */
export function AuditEntityFilter({ entity, onEntityChange }: { entity: string; onEntityChange: (entity: string) => void }) {
  return (
      <select
        aria-label="Filter entitas"
        className="mb-4 h-11 w-full rounded-control border border-line bg-surface px-3 text-sm md:w-auto"
        value={entity}
        onChange={(e) => onEntityChange(e.target.value)}
      >
        <option value="">Semua entitas</option>
        {Object.entries(AUDIT_ENTITIES).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
  );
}
