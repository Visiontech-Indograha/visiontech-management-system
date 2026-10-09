/** Tab "Absensi saya" vs absensi anggota (PM) / umum (Finance, OPS) bagi pemegang wewenang lihat/tinjau. */
export function AttendanceScopeTabs({ scope, teamLabel, onScopeChange }: {
  scope: string;
  teamLabel: string;
  onScopeChange: (scope: "mine" | "team") => void;
}) {
  return (
        <div role="tablist" aria-label="Jenis absensi" className="mb-4 inline-flex rounded-control border border-line bg-surface p-1">
          {([["mine", "Absensi saya"], ["team", teamLabel]] as const).map(([key, label]) => (
            <button
              key={key}
              role="tab"
              type="button"
              aria-selected={scope === key}
              className={`min-h-10 rounded-control px-4 text-sm font-medium ${scope === key ? "bg-primary text-primary-foreground" : "text-mist hover:bg-muted"}`}
              onClick={() => onScopeChange(key)}
            >
              {label}
            </button>
          ))}
        </div>
  );
}
