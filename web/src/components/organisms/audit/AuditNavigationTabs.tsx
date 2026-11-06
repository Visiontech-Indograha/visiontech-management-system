/**
 * web/src/components/organisms/audit/AuditNavigationTabs.tsx
 * Tab navigasi untuk beralih antara Audit Log Aktivitas dan Riwayat cadangan data.
 */

import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";

export function AuditNavigationTabs({
  activeTab,
  onTabChange,
}: {
  activeTab: "activity" | "backups";
  onTabChange: (tab: "activity" | "backups") => void;
}) {
  return (
    <div className="flex items-center gap-2 border-b border-line pb-3">
      <ActionButton
        variant={activeTab === "activity" ? "default" : "outline"}
        size="sm"
        onClick={() => onTabChange("activity")}
        className="text-xs"
      >
        <TextBlock as="span">Aktivitas dan Perubahan Data</TextBlock>
      </ActionButton>
      <ActionButton
        variant={activeTab === "backups" ? "default" : "outline"}
        size="sm"
        onClick={() => onTabChange("backups")}
        className="text-xs"
      >
        <TextBlock as="span">Riwayat cadangan data</TextBlock>
      </ActionButton>
    </div>
  );
}
