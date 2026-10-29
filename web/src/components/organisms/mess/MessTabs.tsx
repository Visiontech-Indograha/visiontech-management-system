import { PlainAction } from "@/components/molecules/PlainAction";
import { TextBlock } from "@/components/molecules/TextBlock";

export type MessTab = "stays" | "requests" | "places";

/** Tab halaman Mess: Hunian, Permintaan (hanya peninjau, dengan jumlah menunggu), Daftar Mess. */
export function MessTabs({
  tab,
  tabs,
  pendingCount,
  onTabChange,
}: {
  tab: MessTab;
  tabs: [MessTab, string][];
  pendingCount: number;
  onTabChange: (tab: MessTab) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Bagian mess"
      className="mb-4 inline-flex rounded-control border border-line bg-surface p-1"
    >
      {tabs.map(([key, label]) => (
        <PlainAction
          key={key}
          role="tab"
          type="button"
          aria-selected={tab === key}
          className={`min-h-10 rounded-control px-4 text-sm font-medium ${tab === key ? "bg-primary text-primary-foreground" : "text-mist hover:bg-muted"}`}
          onClick={() => onTabChange(key)}
        >
          <TextBlock as="span">
            {label}
            {key === "requests" && pendingCount > 0 ? ` (${pendingCount})` : ""}
          </TextBlock>
        </PlainAction>
      ))}
    </div>
  );
}
