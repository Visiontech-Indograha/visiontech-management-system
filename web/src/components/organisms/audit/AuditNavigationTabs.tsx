/**
 * web/src/components/organisms/audit/AuditNavigationTabs.tsx
 * Tab navigasi untuk beralih antara Audit Log Aktivitas dan Registry Backup Basis Data.
 */

import { Button } from "@/components/atoms/Button";
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
      <Button
        variant={activeTab === "activity" ? "default" : "outline"}
        size="sm"
        onClick={() => onTabChange("activity")}
        className="text-xs"
      >
        <TextBlock as="span">Aktivitas & Perubahan Data</TextBlock>
      </Button>
      <Button
        variant={activeTab === "backups" ? "default" : "outline"}
        size="sm"
        onClick={() => onTabChange("backups")}
        className="text-xs"
      >
        <TextBlock as="span">Registry Backup Basis Data</TextBlock>
      </Button>
    </div>
  );
}
